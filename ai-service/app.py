import hashlib
import os
import time
from flask import Flask, jsonify

# Initialize Flask app
app = Flask(__name__)

# Track start time for health endpoint
start_time = time.time()

# ─────────────────────────────────────────────────────────────────────────────
# Redis (optional — graceful fallback if unavailable)
# ─────────────────────────────────────────────────────────────────────────────
_REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
_REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

try:
    import redis as _redis_lib
    cache = _redis_lib.Redis(
        host=_REDIS_HOST,
        port=_REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=2
    )
    cache.ping()
    print(f"[OK] Redis connected at {_REDIS_HOST}:{_REDIS_PORT}")
except Exception:
    cache = None
    print(f"[WARN] Redis not available at {_REDIS_HOST}:{_REDIS_PORT} — running without cache")

from services.cache_service import CacheService
cache_service = CacheService(cache)

# ─────────────────────────────────────────────────────────────────────────────
# ChromaDB (vector store for RAG grounding)
# ─────────────────────────────────────────────────────────────────────────────
try:
    from services.chroma_client import ChromaClient
    _chroma = ChromaClient()
except Exception as e:
    _chroma = None
    print(f"[WARN] ChromaDB init failed: {e}")


def get_chroma():
    return _chroma


def get_cache_service():
    return cache_service


# Import and register blueprints
from routes.describe import describe_bp
from routes.categorise import categorise_bp
from routes.recommend import recommend_bp
from routes.generate_report import generate_report_bp

app.register_blueprint(describe_bp)
app.register_blueprint(categorise_bp)
app.register_blueprint(recommend_bp)
app.register_blueprint(generate_report_bp)


def get_cache_key(prefix: str, text: str) -> str:
    """Deterministic cache key helper kept for backward compatibility."""
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    return f"{prefix}:{digest}"


# ─────────────────────────────────────────────────────────────────────────────
# Health Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health_check():
    uptime_seconds = int(time.time() - start_time)

    chroma_available = _chroma is not None and getattr(_chroma, '_available', False)
    doc_count = 0
    corpus_ver = "unavailable"
    if chroma_available:
        try:
            doc_count = _chroma.count()
            corpus_ver = _chroma.get_corpus_version()
        except Exception:
            pass

    redis_ok = cache_service.is_available()

    return jsonify({
        "status": "healthy",
        "model_name": "llama-3.3-70b-versatile",
        "uptime": f"{uptime_seconds}s",
        "chromadb_docs": doc_count,
        "chromadb_available": chroma_available,
        "corpus_version": corpus_ver,
        "redis_available": redis_ok,
        "cache_enabled": cache_service.enabled,
        "pydantic_validation": True,
        "rag_grounding_active": chroma_available and doc_count > 0,
        "api_port": 5000
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
