import hashlib
import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from services.groq_client import GroqClient
from services.rag_service import retrieve_rag_context, REQUIRE_GROUNDING
from services.cache_service import compute_cache_key
from schemas import DescribeRequest, DescribeResponse, format_validation_error

describe_bp = Blueprint('describe', __name__)

_groq = GroqClient()
MODEL_ID = "llama-3.3-70b-versatile"


def _load_prompt():
    """Load the describe prompt template."""
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'describe_prompt.txt')
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def _get_prompt_version():
    try:
        content = _load_prompt()
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]
    except Exception:
        return "v1"


@describe_bp.route('/describe', methods=['POST'])
def describe():
    from app import get_chroma, get_cache_service
    chroma = get_chroma()
    cache_svc = get_cache_service()

    # 1. Pydantic Request Validation
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Bad Request: Missing JSON body"}), 400

    try:
        req = DescribeRequest.model_validate(data)
    except ValidationError as e:
        return jsonify(format_validation_error(e)), 400

    corpus_ver = chroma.get_corpus_version() if chroma else "none"
    prompt_ver = _get_prompt_version()
    rag_settings = {
        "top_k": int(os.environ.get("CHROMA_TOP_K", "3")),
        "max_dist": os.environ.get("CHROMA_MAX_DISTANCE", "none"),
        "req_ground": os.environ.get("REQUIRE_GROUNDING", "false").lower()
    }

    # 2. Redis Cache Lookup
    cache_key = compute_cache_key("describe", req.input_text, prompt_ver, MODEL_ID, corpus_ver, rag_settings)
    cached_result = cache_svc.get(cache_key)
    if cached_result is not None:
        return jsonify(cached_result), 200

    # 3. RAG Retrieval from ChromaDB
    grounded, context_block, citations, disclaimer = retrieve_rag_context(chroma, req.input_text)

    if REQUIRE_GROUNDING and not grounded:
        return jsonify({
            "error": "Insufficient source context in knowledge base to generate grounded output",
            "grounded": False,
            "citations": []
        }), 422

    # 4. Format Prompt with Context
    try:
        prompt_template = _load_prompt()
        formatted_prompt = prompt_template.replace('{user_input}', req.input_text)
        formatted_prompt = formatted_prompt.replace('{context_block}', context_block)
    except Exception:
        return jsonify({"error": "Internal Server Error: Failed to load prompt"}), 500

    # 5. Call Groq
    messages = [{"role": "user", "content": formatted_prompt}]
    raw_ai = _groq.call_for_json(messages, temperature=0.3, max_tokens=500)

    if raw_ai is None:
        return jsonify({"error": "AI service temporarily unavailable. Please retry."}), 503

    if not isinstance(raw_ai, dict) or "professional_description" not in raw_ai:
        return jsonify({"error": "AI returned an unexpected response format."}), 502

    # 6. Pydantic Response Validation
    try:
        response_model = DescribeResponse(
            professional_description=raw_ai["professional_description"],
            generated_at=datetime.now(timezone.utc).isoformat(),
            grounded=grounded,
            citations=citations,
            disclaimer=disclaimer
        )
    except ValidationError as e:
        return jsonify({"error": f"AI response validation error: {e.errors()}"}), 502

    result_dict = response_model.model_dump()

    # 7. Write to Redis Cache
    cache_svc.set(cache_key, result_dict)

    return jsonify(result_dict), 200
