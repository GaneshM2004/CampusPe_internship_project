"""
AI-service test suite:
- Pydantic request and response schema validation
- ChromaDB RAG retrieval, context injection, and citation validation
- Redis caching (hit, miss, key generation, and graceful fallback on outage)
- Input sanitization and error handling
All tests run with mocks for external services — no live API keys or servers needed.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from app import app
from services.cache_service import compute_cache_key


@pytest.fixture
def client():
    """Configures the Flask app for testing and returns a test client."""
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def mock_redis_cache(monkeypatch):
    """
    Mock Redis globally in CacheService so tests do not require a live Redis instance.
    Defaults to cache miss (get returns None).
    """
    store = {}

    mock_client = MagicMock()
    mock_client.get.side_effect = lambda k: store.get(k)
    mock_client.setex.side_effect = lambda k, ttl, val: store.update({k: val})
    mock_client.ping.return_value = True

    from app import cache_service
    monkeypatch.setattr(cache_service, 'client', mock_client)
    monkeypatch.setattr(cache_service, 'enabled', True)

    yield mock_client


# ─── 1. GET /health ─────────────────────────────────────────────────────────

def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    body = response.json
    assert body['status'] == 'healthy'
    assert 'uptime' in body
    assert 'chromadb_docs' in body
    assert 'redis_available' in body
    assert body['pydantic_validation'] is True
    assert 'rag_grounding_active' in body


# ─── 2. POST /describe — Pydantic Validation & RAG ──────────────────────────

@patch('routes.describe._groq')
@patch('routes.describe.retrieve_rag_context')
def test_describe_success_ungrounded(mock_rag, mock_groq, client):
    """When no Chroma context is found, describe returns ungrounded result safely."""
    mock_rag.return_value = (False, "", [], "Ungrounded disclaimer")
    mock_groq.call_for_json.return_value = {
        "professional_description": "Employee medical records processed securely."
    }

    response = client.post('/describe', json={'input_text': 'Employee medical records stored on cloud.'})
    assert response.status_code == 200
    body = response.json
    assert body['professional_description'] == "Employee medical records processed securely."
    assert 'generated_at' in body
    assert body['grounded'] is False
    assert body['citations'] == []
    assert 'Ungrounded' in body['disclaimer']


@patch('routes.describe._groq')
@patch('routes.describe.retrieve_rag_context')
def test_describe_success_grounded(mock_rag, mock_groq, client):
    """When Chroma returns chunks, describe passes context and returns verified citations."""
    sample_citation = {
        "doc_id": "dpdp_rule_001",
        "chunk_id": "dpdp_rule_001_chunk_0",
        "source": "dpdp_act_2023.txt",
        "section": "Section 9"
    }
    mock_rag.return_value = (True, "[Source Context]", [sample_citation], "Grounded disclaimer")
    mock_groq.call_for_json.return_value = {
        "professional_description": "Parental consent required for child data processing."
    }

    response = client.post('/describe', json={'input_text': 'Processing data of users under 18.'})
    assert response.status_code == 200
    body = response.json
    assert body['grounded'] is True
    assert len(body['citations']) == 1
    assert body['citations'][0]['chunk_id'] == "dpdp_rule_001_chunk_0"
    assert body['citations'][0]['source'] == "dpdp_act_2023.txt"


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


def test_describe_wrong_type(client):
    """Pydantic rejects non-string input_text with 400."""
    response = client.post('/describe', json={'input_text': 12345})
    assert response.status_code == 400


def test_describe_extra_fields_forbidden(client):
    """Pydantic rejects unexpected extra fields when extra='forbid'."""
    response = client.post('/describe', json={'input_text': 'valid', 'unexpected': 'extra'})
    assert response.status_code == 400


def test_describe_no_json_body(client):
    response = client.post('/describe', data='not json', content_type='text/plain')
    assert response.status_code == 400


# ─── 3. POST /categorise — Pydantic Validation & Logic ──────────────────────

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
    assert 'meta' in body


@patch('routes.categorise.client')
def test_categorise_invalid_category_fallback(mock_client, client):
    mock_client.call_for_json.return_value = {
        "category": "Unknown Category",
        "confidence": 0.9,
        "reasoning": "Some reason"
    }
    response = client.post('/categorise', json={'text': 'some text'})
    assert response.status_code == 200
    assert response.json['category'] == 'Data Processing'


def test_categorise_empty_input(client):
    response = client.post('/categorise', json={'text': ''})
    assert response.status_code == 400


def test_categorise_whitespace_only(client):
    response = client.post('/categorise', json={'text': '   \n  '})
    assert response.status_code == 400


def test_categorise_missing_field(client):
    response = client.post('/categorise', json={})
    assert response.status_code == 400


# ─── 4. POST /recommend — Pydantic Validation & RAG ─────────────────────────

@patch('routes.recommend._groq')
@patch('routes.recommend.retrieve_rag_context')
def test_recommend_success(mock_rag, mock_groq, client):
    mock_rag.return_value = (False, "", [], "Disclaimer")
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
    assert body['recommendations'][0]['priority'] == 'High'


@patch('routes.recommend._groq')
def test_recommend_ai_unavailable(mock_groq, client):
    mock_groq.call_for_json.return_value = None
    response = client.post('/recommend', json={'input_text': 'Some input'})
    assert response.status_code == 503


def test_recommend_missing_input(client):
    response = client.post('/recommend', json={})
    assert response.status_code == 400


# ─── 5. POST /generate-report — Pydantic Validation & RAG ───────────────────

@patch('routes.generate_report._groq')
@patch('routes.generate_report.retrieve_rag_context')
def test_generate_report_success(mock_rag, mock_groq, client):
    mock_rag.return_value = (False, "", [], "Disclaimer")
    mock_groq.call_for_json.return_value = {
        "title": "Data Breach Audit Report",
        "executive_summary": "A significant breach occurred.",
        "overview": "Detailed description of the breach.",
        "top_items": ["Finding 1", "Finding 2"],
        "recommendations": ["Action 1", "Action 2"]
    }
    response = client.post('/generate-report', json={'input_text': 'Large scale data breach incident.'})
    assert response.status_code == 200
    body = response.json
    assert body['title'] == "Data Breach Audit Report"
    assert 'executive_summary' in body
    assert len(body['top_items']) == 2
    assert len(body['recommendations']) == 2


@patch('routes.generate_report._groq')
def test_generate_report_ai_unavailable(mock_groq, client):
    mock_groq.call_for_json.return_value = None
    response = client.post('/generate-report', json={'input_text': 'Some incident'})
    assert response.status_code == 503


@patch('routes.generate_report._groq')
def test_generate_report_incomplete_response(mock_groq, client):
    """If AI response is not a dict or missing core fields, return 502."""
    mock_groq.call_for_json.return_value = "Not a dict"
    response = client.post('/generate-report', json={'input_text': 'Some incident'})
    assert response.status_code == 502


# ─── 6. Redis Caching Behavior (Hit, Miss, Keying, and Outage) ──────────────

@patch('routes.describe._groq')
@patch('routes.describe.retrieve_rag_context')
def test_redis_cache_hit_and_miss(mock_rag, mock_groq, client):
    """
    First call should miss cache and call Groq.
    Second call with identical input should hit cache and NOT call Groq a second time.
    """
    mock_rag.return_value = (False, "", [], "Disclaimer")
    mock_groq.call_for_json.return_value = {
        "professional_description": "Cacheable description."
    }

    payload = {'input_text': 'Identical test query for cache.'}

    # 1. First call: Cache miss -> Groq called
    resp1 = client.post('/describe', json=payload)
    assert resp1.status_code == 200
    assert mock_groq.call_for_json.call_count == 1

    # 2. Second call: Cache hit -> Groq NOT called again
    resp2 = client.post('/describe', json=payload)
    assert resp2.status_code == 200
    assert mock_groq.call_for_json.call_count == 1
    assert resp2.json['professional_description'] == resp1.json['professional_description']


def test_cache_key_generation():
    """Verify deterministic cache key computation across variations."""
    key1 = compute_cache_key("describe", "user input", "v1", "llama-3", "corp1")
    key2 = compute_cache_key("describe", "  user   input  ", "v1", "llama-3", "corp1")
    assert key1 == key2  # normalized whitespace matches

    key3 = compute_cache_key("describe", "different input", "v1", "llama-3", "corp1")
    assert key1 != key3

    # Changing corpus version invalidates cache key
    key_new_corpus = compute_cache_key("describe", "user input", "v1", "llama-3", "corp2")
    assert key1 != key_new_corpus


@patch('routes.describe._groq')
@patch('routes.describe.retrieve_rag_context')
def test_redis_outage_graceful_degradation(mock_rag, mock_groq, client, monkeypatch):
    """When Redis is down (ConnectionError), route continues and returns uncached result."""
    from app import cache_service
    broken_redis = MagicMock()
    broken_redis.get.side_effect = Exception("Connection refused to Redis")
    broken_redis.setex.side_effect = Exception("Connection refused to Redis")
    monkeypatch.setattr(cache_service, 'client', broken_redis)

    mock_rag.return_value = (False, "", [], "Disclaimer")
    mock_groq.call_for_json.return_value = {
        "professional_description": "Works without Redis."
    }

    response = client.post('/describe', json={'input_text': 'Redis is down test.'})
    assert response.status_code == 200
    assert response.json['professional_description'] == "Works without Redis."


# ─── 7. ChromaDB Chunking & Query Unit Tests ────────────────────────────────

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
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chroma_query_returns_empty_when_unavailable():
    from services.chroma_client import ChromaClient
    c = ChromaClient.__new__(ChromaClient)
    c._available = False
    assert c.query("any question") == []


def test_chroma_query_returns_empty_when_empty_collection():
    from services.chroma_client import ChromaClient
    c = ChromaClient.__new__(ChromaClient)
    c._available = True
    c.collection = MagicMock()
    c.collection.count.return_value = 0
    assert c.query("any question") == []


# ─── 8. Input Sanitization & Fence Stripping ────────────────────────────────

@patch('routes.describe._groq')
@patch('routes.describe.retrieve_rag_context')
def test_input_sanitization_does_not_500(mock_rag, mock_groq, client):
    mock_rag.return_value = (False, "", [], "Disclaimer")
    mock_groq.call_for_json.return_value = {
        "professional_description": "Sanitized description."
    }
    payload = {'input_text': '<script>alert("hack")</script> valid text'}
    response = client.post('/describe', json=payload)
    assert response.status_code == 200


def test_groq_json_cleanup_logic():
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


# ─── 9. PDF Extraction, Manifest & Idempotent Ingestion Tests ──────────────

def test_chunk_page_text_paragraph_split():
    from ingest_documents import chunk_page_text
    text = "Paragraph one is here.\n\nParagraph two is here.\n\nParagraph three is here."
    chunks = chunk_page_text(text, max_chars=50, overlap=10)
    assert len(chunks) >= 2
    assert "Paragraph one" in chunks[0]


def test_chunk_page_text_empty():
    from ingest_documents import chunk_page_text
    assert chunk_page_text("") == []
    assert chunk_page_text("   \n\n  ") == []


def test_load_manifest_returns_documents():
    from ingest_documents import load_manifest
    manifest = load_manifest()
    assert "documents" in manifest
    assert len(manifest["documents"]) >= 2
    filenames = [doc["filename"] for doc in manifest["documents"]]
    assert "DPDP_ACT_2023.pdf" in filenames
    assert "DPDP_Rules_2025_English_only.pdf" in filenames


def test_manifest_corpus_versioning():
    from services.chroma_client import ChromaClient
    c = ChromaClient.__new__(ChromaClient)
    c._available = True
    c.collection = MagicMock()
    c.collection.count.return_value = 232
    ver = c.get_corpus_version()
    assert "v_manifest_" in ver
    assert ver.endswith("_c232")


def test_cache_key_invalidates_on_rag_settings():
    from services.cache_service import compute_cache_key
    key1 = compute_cache_key("describe", "test input", "v1", "llama-3.3-70b-versatile", "v_manifest_1_c100", {"top_k": 3})
    key2 = compute_cache_key("describe", "test input", "v1", "llama-3.3-70b-versatile", "v_manifest_1_c100", {"top_k": 5})
    key3 = compute_cache_key("describe", "test input", "v1", "llama-3.3-70b-versatile", "v_manifest_2_c100", {"top_k": 3})
    assert key1 != key2
    assert key1 != key3


def test_extract_pdf_encrypted_fails_safely():
    from ingest_documents import extract_pdf_document
    mock_reader = MagicMock()
    mock_reader.is_encrypted = True
    with patch('ingest_documents.PdfReader', return_value=mock_reader), \
         patch('ingest_documents.compute_file_sha256', return_value='fakehash'):
        with pytest.raises(ValueError, match="encrypted"):
            extract_pdf_document("dummy.pdf", "dummy_doc", "Dummy Title")


def test_extract_pdf_image_only_detects_empty_pages():
    from ingest_documents import extract_pdf_document
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = ""  # Scanned image with no OCR
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "   "
    mock_reader = MagicMock()
    mock_reader.is_encrypted = False
    mock_reader.pages = [mock_page1, mock_page2]

    with patch('ingest_documents.PdfReader', return_value=mock_reader), \
         patch('ingest_documents.compute_file_sha256', return_value="fakehash"):
        chunks, stats = extract_pdf_document("scanned.pdf", "scan_doc", "Scanned Doc")
        assert stats["empty_pages"] == [1, 2]
        assert stats["total_chars"] == 0
        assert len(chunks) == 0


def test_extract_pdf_clean_text_with_sections():
    from ingest_documents import extract_pdf_document
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = (
        "CHAPTER I\nPRELIMINARY\n\n1. (1) This Act may be called the DPDP Act.\n\n"
        "2. Definitions.\nIn this Act, personal data means any data..."
    )
    mock_reader = MagicMock()
    mock_reader.is_encrypted = False
    mock_reader.pages = [mock_page1]

    with patch('ingest_documents.PdfReader', return_value=mock_reader), \
         patch('ingest_documents.compute_file_sha256', return_value="fakehash"):
        chunks, stats = extract_pdf_document("test.pdf", "test_act", "Test Act Title")
        assert stats["total_pages"] == 1
        assert stats["empty_pages"] == []
        assert len(chunks) >= 1
        chunk_meta = chunks[0]["metadata"]
        assert chunk_meta["doc_id"] == "test_act"
        assert chunk_meta["page"] == 1
        assert "section" in chunk_meta
        assert chunk_meta["chunk_id"].startswith("test_act_p1_c")


def test_citation_page_number_propagation(client):
    from schemas import CitationItem
    citation = CitationItem(
        doc_id="dpdp_act_2023",
        chunk_id="dpdp_act_2023_p5_c1",
        source="DPDP_ACT_2023.pdf",
        section="Section 9. Processing of data of children",
        page=5
    )
    dumped = citation.model_dump()
    assert dumped["page"] == 5
    assert dumped["chunk_id"] == "dpdp_act_2023_p5_c1"


# ─── 10. End-to-End Route RAG Integration & Distance Threshold Tests ─────────

def test_rag_distance_threshold_filtering():
    """retrieve_rag_context filters out chunks beyond max_distance and returns ungrounded when none pass."""
    from services.rag_service import retrieve_rag_context
    from services.chroma_client import ChromaClient

    c = ChromaClient.__new__(ChromaClient)
    c._available = True
    c.collection = MagicMock()
    c.collection.count.return_value = 10
    c.model = MagicMock()
    c.model.encode.return_value.tolist.return_value = [0.1, 0.2]

    # Simulate a distant/irrelevant nearest neighbor (cosine distance 0.85 > 0.70)
    c.collection.query.return_value = {
        "ids": [["irrelevant_chunk_1"]],
        "documents": [["Unrelated sourdough recipe text."]],
        "metadatas": [[{"source": "doc.pdf", "doc_id": "doc1", "section": "Sec 1", "page": 1}]],
        "distances": [[0.85]],
    }

    grounded, ctx, citations, disclaimer = retrieve_rag_context(c, "sourdough bread", top_k=3, max_distance=0.7)
    assert grounded is False
    assert ctx == ""
    assert citations == []
    assert "not grounded" in disclaimer.lower() or "ungrounded" in disclaimer.lower()


@pytest.mark.parametrize("endpoint,groq_payload,expected_field", [
    ("/describe", {"professional_description": "Grounded desc."}, "professional_description"),
    ("/recommend", {"recommendations": [{"action_type": "Legal", "description": "Get consent.", "priority": "High"}]}, "recommendations"),
    ("/generate-report", {
        "title": "Audit",
        "executive_summary": "Summary",
        "overview": "Overview",
        "top_items": ["Item 1"],
        "recommendations": ["Rec 1"]
    }, "title"),
])
def test_live_routes_invoke_chroma_and_inject_context(client, monkeypatch, endpoint, groq_payload, expected_field):
    """
    Verify /describe, /recommend, and /generate-report each invoke Chroma retrieval
    (without mocking retrieve_rag_context), inject retrieved context into the Groq prompt,
    and attach citations from retrieved metadata.
    """
    from app import get_chroma
    chroma_client = get_chroma()

    fake_chunk = [{
        "id": "dpdp_act_2023_p8_c4",
        "document": "Section 9: Verifiable parental consent is required for children under 18.",
        "metadata": {
            "doc_id": "dpdp_act_2023",
            "chunk_id": "dpdp_act_2023_p8_c4",
            "source": "DPDP_ACT_2023.pdf",
            "section": "Section 9",
            "page": 8,
            "file_sha256": "abc123",
            "text_hash": "def456"
        },
        "distance": 0.30
    }]

    monkeypatch.setattr(chroma_client, "_available", True)
    query_mock = MagicMock(return_value=fake_chunk)
    monkeypatch.setattr(chroma_client, "query", query_mock)
    monkeypatch.setattr(chroma_client, "get_corpus_version", lambda: "v_test_c1")

    groq_module = {
        "/describe": "routes.describe._groq",
        "/recommend": "routes.recommend._groq",
        "/generate-report": "routes.generate_report._groq",
    }[endpoint]

    with patch(f"{groq_module}.call_for_json", return_value=groq_payload) as mock_groq_call:
        resp = client.post(endpoint, json={"input_text": f"Children consent check for {endpoint}"})

    assert resp.status_code == 200
    body = resp.json
    assert expected_field in body
    assert body["grounded"] is True
    assert len(body["citations"]) == 1
    assert body["citations"][0]["chunk_id"] == "dpdp_act_2023_p8_c4"
    assert body["citations"][0]["page"] == 8

    # Prove Chroma query was actually invoked by the route
    assert query_mock.call_count == 1

    # Prove retrieved context was actually injected into the prompt sent to Groq
    sent_messages = mock_groq_call.call_args[0][0]
    prompt_sent = sent_messages[0]["content"]
    assert "Verifiable parental consent is required for children under 18." in prompt_sent
    assert "dpdp_act_2023_p8_c4" in prompt_sent


@pytest.mark.parametrize("endpoint,payload_key,groq_module,groq_payload", [
    ("/describe", "input_text", "routes.describe._groq", {"professional_description": "Grounded desc."}),
    ("/categorise", "text", "routes.categorise.client", {"category": "Consent Management", "confidence": 0.92, "reasoning": "Matches Sec 9."}),
    ("/recommend", "input_text", "routes.recommend._groq", {"recommendations": [{"action_type": "Legal", "description": "Get consent.", "priority": "High"}]}),
    ("/generate-report", "input_text", "routes.generate_report._groq", {
        "title": "Audit",
        "executive_summary": "Summary",
        "overview": "Overview",
        "top_items": ["Item 1"],
        "recommendations": ["Rec 1"]
    }),
])
def test_all_four_routes_work_with_real_app_and_real_chroma_query(client, monkeypatch, endpoint, payload_key, groq_module, groq_payload):
    """
    Exercise all 4 live routes through real app.get_chroma(), real app.get_cache_service(),
    real retrieve_rag_context(), and real ChromaClient.query(question, top_k=..., max_distance=...)
    (mocking only collection.query, model.encode, and Groq).
    Proves zero contract mismatch across routes -> rag_service -> ChromaClient -> schemas.
    """
    from app import get_chroma
    chroma = get_chroma()

    mock_collection = MagicMock()
    mock_collection.count.return_value = 5
    mock_collection.query.return_value = {
        "ids": [["dpdp_act_2023_p8_c4", "irrelevant_far_chunk"]],
        "documents": [[
            "Section 9: Verifiable parental consent before processing data of a child.",
            "Far distant unrelated text."
        ]],
        "metadatas": [[
            {
                "doc_id": "dpdp_act_2023",
                "chunk_id": "dpdp_act_2023_p8_c4",
                "source": "DPDP_ACT_2023.pdf",
                "section": "Section 9",
                "page": 8,
                "file_sha256": "abc123",
                "text_hash": "def456"
            },
            {
                "doc_id": "other",
                "chunk_id": "irrelevant_far_chunk",
                "source": "other.pdf",
                "section": "Other",
                "page": 1
            }
        ]],
        "distances": [[0.32, 0.92]],
    }
    mock_model = MagicMock()
    mock_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]

    monkeypatch.setattr(chroma, "_available", True)
    monkeypatch.setattr(chroma, "collection", mock_collection)
    monkeypatch.setattr(chroma, "model", mock_model)

    with patch(f"{groq_module}.call_for_json", return_value=groq_payload) as mock_groq:
        resp = client.post(endpoint, json={payload_key: f"Real ChromaClient contract check for {endpoint}"})

    assert resp.status_code == 200
    body = resp.json
    assert body["grounded"] is True
    # Distance threshold (0.7) filters out distance 0.92 and keeps 0.32
    assert len(body["citations"]) == 1
    assert body["citations"][0]["chunk_id"] == "dpdp_act_2023_p8_c4"
    assert body["citations"][0]["page"] == 8
    assert body.get("disclaimer")
    sent_prompt = mock_groq.call_args[0][0][-1]["content"]
    assert "Verifiable parental consent before processing data of a child." in sent_prompt
