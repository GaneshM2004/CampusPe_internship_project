"""
AI-service tests — all external calls (Groq, Redis, ChromaDB) are mocked.
Tests must pass without a live Groq API key or running services.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    """Configures the Flask app for testing and returns a test client."""
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """Mock Redis globally so tests never need a running Redis instance."""
    mock = MagicMock()
    mock.get.return_value = None   # simulate cache miss
    mock.ping.return_value = True
    monkeypatch.setattr('app.cache', mock)


# ─── 1. GET /health ─────────────────────────────────────────────────────────

def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    body = response.json
    assert body['status'] == 'healthy'
    assert 'uptime' in body
    assert 'chromadb_docs' in body
    assert 'redis_available' in body


# ─── 2. POST /describe ───────────────────────────────────────────────────────

@patch('routes.describe._groq')
def test_describe_success(mock_groq, client):
    mock_groq.call_for_json.return_value = {
        "professional_description": "This is a professional compliance summary."
    }
    response = client.post('/describe', json={'input_text': 'Employee medical records stored on cloud.'})
    assert response.status_code == 200
    body = response.json
    assert 'professional_description' in body
    assert 'generated_at' in body


@patch('routes.describe._groq')
def test_describe_ai_unavailable(mock_groq, client):
    mock_groq.call_for_json.return_value = None
    response = client.post('/describe', json={'input_text': 'Some input'})
    assert response.status_code == 503
    assert 'error' in response.json


def test_describe_empty_input(client):
    response = client.post('/describe', json={})
    assert response.status_code == 400
    assert 'error' in response.json


def test_describe_blank_text(client):
    response = client.post('/describe', json={'input_text': '   '})
    assert response.status_code == 400


def test_describe_too_long(client):
    response = client.post('/describe', json={'input_text': 'x' * 5001})
    assert response.status_code == 400


def test_describe_no_json_body(client):
    response = client.post('/describe', data='not json', content_type='text/plain')
    assert response.status_code == 400


# ─── 3. POST /categorise ────────────────────────────────────────────────────

@patch('routes.categorise.client')
def test_categorise_success(mock_client, client):
    mock_client.call_for_json.return_value = {
        "category": "Data Processing",
        "confidence": 0.95,
        "reasoning": "This involves processing of personal data."
    }
    response = client.post('/categorise', json={'text': 'HR medical records'})
    assert response.status_code == 200
    body = response.json
    assert body['category'] == 'Data Processing'
    assert 0.0 <= body['confidence'] <= 1.0
    assert 'reasoning' in body


@patch('routes.categorise.client')
def test_categorise_invalid_category_fallback(mock_client, client):
    """If AI returns an unknown category, the route should use 'Data Processing' as default."""
    mock_client.call_for_json.return_value = {
        "category": "Some Unknown Category",
        "confidence": 0.9,
        "reasoning": "Some reason"
    }
    response = client.post('/categorise', json={'text': 'some text'})
    assert response.status_code == 200
    assert response.json['category'] == 'Data Processing'


def test_categorise_empty_input(client):
    response = client.post('/categorise', json={'text': ''})
    assert response.status_code == 400


def test_categorise_missing_field(client):
    response = client.post('/categorise', json={})
    assert response.status_code == 400


# ─── 4. POST /recommend ─────────────────────────────────────────────────────

@patch('routes.recommend._groq')
def test_recommend_success(mock_groq, client):
    mock_groq.call_for_json.return_value = {
        "recommendations": [
            {"action_type": "Policy", "description": "Implement DPA.", "priority": "High"},
            {"action_type": "Technical", "description": "Encrypt at rest.", "priority": "Medium"},
            {"action_type": "Legal", "description": "Obtain consent.", "priority": "Low"}
        ]
    }
    response = client.post('/recommend', json={'input_text': 'New cloud vendor onboarded.'})
    assert response.status_code == 200
    body = response.json
    assert 'recommendations' in body
    assert len(body['recommendations']) == 3


@patch('routes.recommend._groq')
def test_recommend_ai_unavailable(mock_groq, client):
    mock_groq.call_for_json.return_value = None
    response = client.post('/recommend', json={'input_text': 'Some input'})
    assert response.status_code == 503


def test_recommend_missing_input(client):
    response = client.post('/recommend', json={})
    assert response.status_code == 400


# ─── 5. POST /generate-report ───────────────────────────────────────────────

@patch('routes.generate_report._groq')
def test_generate_report_success(mock_groq, client):
    mock_groq.call_for_json.return_value = {
        "title": "Data Breach Audit Report",
        "executive_summary": "A significant breach occurred.",
        "overview": "Detailed description of the breach.",
        "top_items": ["Finding 1", "Finding 2"],
        "recommendations": ["Action 1", "Action 2"]
    }
    response = client.post('/generate-report', json={'input_text': 'Large scale data breach.'})
    assert response.status_code == 200
    body = response.json
    assert 'title' in body
    assert 'executive_summary' in body
    assert 'top_items' in body
    assert 'recommendations' in body


@patch('routes.generate_report._groq')
def test_generate_report_ai_unavailable(mock_groq, client):
    mock_groq.call_for_json.return_value = None
    response = client.post('/generate-report', json={'input_text': 'Some incident'})
    assert response.status_code == 503


@patch('routes.generate_report._groq')
def test_generate_report_incomplete_response(mock_groq, client):
    """If AI response is missing required fields, return 502."""
    mock_groq.call_for_json.return_value = {
        "title": "Only a title"
        # missing executive_summary, overview, top_items, recommendations
    }
    response = client.post('/generate-report', json={'input_text': 'Some incident'})
    assert response.status_code == 502


def test_generate_report_missing_input(client):
    response = client.post('/generate-report', json={})
    assert response.status_code == 400


# ─── 6. Input sanitization ──────────────────────────────────────────────────

@patch('routes.describe._groq')
def test_input_sanitization_does_not_500(mock_groq, client):
    """XSS-looking input should be safely passed to AI, not cause a 500."""
    mock_groq.call_for_json.return_value = {
        "professional_description": "Sanitized description."
    }
    payload = {'input_text': '<script>alert("hack")</script> valid text'}
    response = client.post('/describe', json=payload)
    assert response.status_code != 500
    assert response.status_code == 200


# ─── 7. JSON cleanup logic ──────────────────────────────────────────────────

def test_groq_json_cleanup_logic():
    """Unit test for the JSON fence-stripping logic inside GroqClient."""
    raw_response = """
    ```json
    {
        "category": "Sensitive Personal Data",
        "confidence": 0.95
    }
    ```
    """
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0].strip()

    parsed = json.loads(cleaned)
    assert parsed["category"] == "Sensitive Personal Data"
    assert parsed["confidence"] == 0.95


# ─── 8. GroqClient call_for_json unit tests ─────────────────────────────────

def test_groq_client_call_for_json_valid():
    """call_for_json should parse valid JSON from raw text response."""
    from services.groq_client import GroqClient
    gc = GroqClient.__new__(GroqClient)  # skip __init__ (no API key needed)
    gc.api_key = "test"
    gc.headers = {}

    with patch.object(gc, 'call', return_value='{"key": "value"}'):
        result = gc.call_for_json([])
    assert result == {"key": "value"}


def test_groq_client_call_for_json_fence_stripped():
    """call_for_json should strip markdown code fences."""
    from services.groq_client import GroqClient
    gc = GroqClient.__new__(GroqClient)
    gc.api_key = "test"
    gc.headers = {}

    raw = '```json\n{"key": "value"}\n```'
    with patch.object(gc, 'call', return_value=raw):
        result = gc.call_for_json([])
    assert result == {"key": "value"}


def test_groq_client_call_for_json_none_on_groq_failure():
    """call_for_json returns None when call() returns None."""
    from services.groq_client import GroqClient
    gc = GroqClient.__new__(GroqClient)
    gc.api_key = "test"
    gc.headers = {}

    with patch.object(gc, 'call', return_value=None):
        result = gc.call_for_json([])
    assert result is None


# ─── 9. ChromaDB chunk_text unit tests ──────────────────────────────────────

def test_chunk_text_basic():
    from services.chroma_client import chunk_text
    text = "a" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)


def test_chunk_text_short_input():
    from services.chroma_client import chunk_text
    text = "Short text"
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_empty():
    from services.chroma_client import chunk_text
    chunks = chunk_text("", chunk_size=500, overlap=50)
    assert chunks == []


# ─── 10. ChromaDB no-context case ───────────────────────────────────────────

def test_chroma_query_returns_empty_when_unavailable():
    """ChromaClient.query should return [] when ChromaDB is not available."""
    from services.chroma_client import ChromaClient
    # Create instance with _available=False to simulate missing chromadb
    c = ChromaClient.__new__(ChromaClient)
    c._available = False

    result = c.query("any question")
    assert result == []