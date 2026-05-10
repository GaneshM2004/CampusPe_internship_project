import hashlib
import threading
import time
from flask import Flask, request, jsonify

# Initialize Flask app
app = Flask(__name__)

# Track start time for health endpoint
start_time = time.time()

# Initialize Redis (optional — graceful fallback if not available)
try:
    import redis
    cache = redis.Redis(host='localhost', port=6379, decode_responses=True)
    cache.ping()  # Test the connection
    print("[OK] Redis connected")
except Exception:
    cache = None
    print("[WARN] Redis not available - running without cache")

# Import and register blueprints
from routes.describe import describe_bp
from routes.categorise import categorise_bp
from routes.recommend import recommend_bp
from routes.generate_report import generate_report_bp

app.register_blueprint(describe_bp)
app.register_blueprint(categorise_bp)
app.register_blueprint(recommend_bp)
app.register_blueprint(generate_report_bp)

# Helper to create a unique key based on the input text
def get_cache_key(text):
    return hashlib.sha256(text.encode()).hexdigest()

# ─────────────────────────────────────────────────────────────────────────────
# Health Endpoint (Day 7)
# [cite: 73] Return model name, doc count, and uptime
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health_check():
    uptime_seconds = int(time.time() - start_time)
    
    # Get document count from ChromaDB
    # from services.chroma_client import ChromaClient
    # chroma_client = ChromaClient()
    # doc_count = chroma_client.collection.count()
    
    # For now, use a placeholder; update with actual ChromaDB count when integrated
    doc_count = 0
    
    return jsonify({
        "status": "healthy",
        "model_name": "llama-3.3-70b-versatile",
        "uptime": f"{uptime_seconds}s",
        "chromadb_docs": doc_count,
        "api_port": 5000
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)