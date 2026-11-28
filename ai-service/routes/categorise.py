import hashlib
import os
import time
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from services.groq_client import GroqClient
from services.rag_service import retrieve_rag_context, REQUIRE_GROUNDING
from services.cache_service import compute_cache_key
from schemas import (
    CategoriseRequest,
    CategoriseResponse,
    CategoriseMeta,
    DPDP_CATEGORIES,
    format_validation_error,
)

categorise_bp = Blueprint("categorise", __name__)
client = GroqClient()
MODEL_ID = "llama-3.3-70b-versatile"
PROMPT_VERSION = "cat_v1"

INFORMATIONAL_DISCLAIMER = (
    "Informational assistance only. This classification is AI-generated and does not "
    "constitute legal advice, regulatory guidance, or a determination of compliance."
)

FALLBACK_RESPONSE = {
    "category": "Data Processing",
    "confidence": 0.0,
    "reasoning": "AI service temporarily unavailable. Please retry.",
    "meta": {
        "model_used": MODEL_ID,
        "tokens_used": 0,
        "response_time_ms": 0,
        "cached": False,
        "is_fallback": True,
    },
    "grounded": False,
    "citations": [],
    "disclaimer": INFORMATIONAL_DISCLAIMER
}


@categorise_bp.route("/categorise", methods=["POST"])
def categorise():
    from app import get_chroma, get_cache_service
    chroma = get_chroma()
    cache_svc = get_cache_service()

    # 1. Pydantic Request Validation
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Bad Request: Missing JSON body"}), 400

    try:
        req = CategoriseRequest.model_validate(data)
    except ValidationError as e:
        return jsonify(format_validation_error(e)), 400

    corpus_ver = chroma.get_corpus_version() if chroma else "none"
    rag_settings = {
        "top_k": int(os.environ.get("CHROMA_TOP_K", "3")),
        "max_dist": os.environ.get("CHROMA_MAX_DISTANCE", "none"),
        "req_ground": os.environ.get("REQUIRE_GROUNDING", "false").lower()
    }

    # 2. Redis Cache Lookup
    cache_key = compute_cache_key("categorise", req.text, PROMPT_VERSION, MODEL_ID, corpus_ver, rag_settings)
    cached_result = cache_svc.get(cache_key)
    if cached_result is not None:
        cached_result.setdefault("meta", {})["cached"] = True
        return jsonify(cached_result), 200

    # 3. RAG Retrieval from ChromaDB
    grounded, context_block, citations, _ = retrieve_rag_context(chroma, req.text)

    if REQUIRE_GROUNDING and not grounded:
        return jsonify({
            "error": "Insufficient source context in knowledge base to categorise compliance item",
            "grounded": False,
            "citations": [],
            "disclaimer": INFORMATIONAL_DISCLAIMER
        }), 422

    categories_str = " | ".join(DPDP_CATEGORIES)

    system_content = (
        "You are a DPDP Act (Digital Personal Data Protection Act) compliance expert. "
        "Respond ONLY in valid JSON. No extra text, no markdown fences."
    )

    user_content = (
        f"Classify this compliance item into ONE of these categories:\n"
        f"{categories_str}\n\n"
        f"Compliance Item: {req.text}\n"
    )
    if context_block:
        user_content += f"\n{context_block}\n"

    user_content += (
        f"\nRespond with ONLY this JSON:\n"
        f'{{"category": "one of the categories above", '
        f'"confidence": 0.95, '
        f'"reasoning": "one clear sentence explaining the classification"}}'
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content}
    ]

    start = time.time()
    raw_ai = client.call_for_json(messages, temperature=0.1)
    elapsed_ms = int((time.time() - start) * 1000)

    # 4. Fallback if AI failed
    if raw_ai is None:
        return jsonify(FALLBACK_RESPONSE), 200

    # 5. Normalize and Validate
    cat = raw_ai.get("category")
    if cat not in DPDP_CATEGORIES:
        cat = "Data Processing"

    try:
        conf = float(raw_ai.get("confidence", 0.5))
    except (TypeError, ValueError):
        conf = 0.5
    conf = max(0.0, min(1.0, conf))

    # 6. Pydantic Response Validation
    response_model = CategoriseResponse(
        category=cat,
        confidence=conf,
        reasoning=str(raw_ai.get("reasoning", "")),
        meta=CategoriseMeta(
            model_used=MODEL_ID,
            tokens_used=0,
            response_time_ms=elapsed_ms,
            cached=False,
            is_fallback=False
        ),
        grounded=grounded,
        citations=citations,
        disclaimer=INFORMATIONAL_DISCLAIMER
    )

    result_dict = response_model.model_dump()

    # 7. Write to Redis Cache
    cache_svc.set(cache_key, result_dict)

    return jsonify(result_dict), 200
