import os
from flask import Blueprint, request, jsonify
from services.groq_client import GroqClient

recommend_bp = Blueprint('recommend', __name__)

# Use the shared GroqClient (testable via mocks)
_groq = GroqClient()


def _load_prompt():
    """Load the recommend prompt template."""
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'recommend_prompt.txt')
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


@recommend_bp.route('/recommend', methods=['POST'])
def recommend():
    # 1. Validate Input
    data = request.get_json(silent=True)
    if not data or 'input_text' not in data:
        return jsonify({"error": "Bad Request: Missing 'input_text' in JSON body"}), 400

    raw_input = data['input_text']
    if not isinstance(raw_input, str) or not raw_input.strip():
        return jsonify({"error": "Bad Request: 'input_text' must be a non-empty string"}), 400
    if len(raw_input) > 5000:
        return jsonify({"error": "Bad Request: 'input_text' exceeds 5000 characters"}), 400

    # 2. Load and Format Prompt
    try:
        prompt_template = _load_prompt()
        formatted_prompt = prompt_template.replace('{user_input}', raw_input)
    except Exception:
        return jsonify({"error": "Internal Server Error: Failed to load prompt"}), 500

    # 3. Call Groq via shared GroqClient (mockable in tests)
    messages = [{"role": "user", "content": formatted_prompt}]
    result = _groq.call_for_json(messages, temperature=0.3, max_tokens=1000)

    if result is None:
        return jsonify({"error": "AI service temporarily unavailable. Please retry."}), 503

    # 4. Validate the expected key exists
    if "recommendations" not in result or not isinstance(result["recommendations"], list):
        return jsonify({"error": "AI returned an unexpected response format."}), 502

    return jsonify(result), 200