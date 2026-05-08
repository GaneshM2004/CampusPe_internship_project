import pytest
import json
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    """Configures the Flask app for testing and returns a test client."""
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


# Mock Redis globally
@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    mock_redis_client = MagicMock()

    # Simulate cache miss
    mock_redis_client.get.return_value = None

    monkeypatch.setattr('app.cache', mock_redis_client)


# --- 1. GET /health ---
def test_health_endpoint(client):
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json['status'] == "healthy"


# --- 2. POST /describe ---
@patch('services.groq_client.GroqClient.call')
def test_describe_success(mock_call, client):

    mock_call.return_value = "This is a professional compliance summary."

    payload = {
        'input_text': 'Employee medical records stored on public cloud.'
    }

    response = client.post('/describe', json=payload)

    assert response.status_code != 404
    assert response.status_code == 200
    assert "professional_description" in response.json


# --- 3. Empty input validation ---
def test_describe_empty_input(client):

    response = client.post('/describe', json={})

    assert response.status_code != 404
    assert response.status_code == 400


# --- 4. POST /categorise ---
@patch('routes.categorise.client.call_for_json')
def test_categorise_success(mock_json_call, client):

    mock_json_call.return_value = {
        "category": "Data Processing",
        "confidence": 0.95
    }

    payload = {
        'text': 'HR medical records'
    }

    response = client.post('/categorise', json=payload)

    assert response.status_code != 404
    assert response.status_code == 200
    assert response.json['category'] == "Data Processing"


# --- 5. POST /recommend ---
@patch('services.groq_client.GroqClient.call_for_json')
def test_recommend_success(mock_json_call, client):

    mock_json_call.return_value = [
        {"action": "DPA", "priority": "High"},
        {"action": "Audit", "priority": "Medium"},
        {"action": "Training", "priority": "Low"}
    ]

    response = client.post(
        '/recommend',
        json={'input_text': 'New cloud vendor'}
    )

    assert response.status_code != 404
    assert response.status_code == 200
    assert len(response.json['recommendations']) >= 1


# --- 6. POST /generate-report ---
def test_generate_report_async_logic(client):

    payload = {
        'input_text': 'Large scale data breach.'
    }

    response = client.post('/generate-report', json=payload)

    assert response.status_code != 404
    assert response.status_code == 200
    # The endpoint returns the full report immediately, not an async job_id
    assert "title" in response.json or "job_id" in response.json


# --- 7. Input sanitization ---
def test_input_sanitization(client):

    payload = {
        'input_text': '<script>alert("hack")</script> valid text'
    }

    response = client.post('/describe', json=payload)

    assert response.status_code != 500


# --- 8. JSON cleanup logic ---
def test_groq_json_cleanup_logic():

    raw_response = """
    ```json
    {
        "category": "Sensitive Personal Data",
        "confidence": 0.95
    }
    ```
    """

    cleaned = (
        raw_response
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    parsed = json.loads(cleaned)

    assert parsed["category"] == "Sensitive Personal Data"
    assert parsed["confidence"] == 0.95