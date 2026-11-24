# DPDP Act Compliance Centre

A full-stack compliance assistance application built for the **Digital Personal Data Protection Act, 2023 (India)**. The system pairs a React frontend with a Spring Boot backend (Java 17, Spring Boot 3.2.4) and a Python Flask AI microservice backed by **Groq Cloud LLM** (`llama-3.3-70b-versatile`), an embedded **ChromaDB vector store** (sentence-transformers), and a **Redis 7 caching layer**.

> **Legal Disclaimer:** This application provides **informational assistance only**. It is not a substitute for qualified legal advice. AI-generated output cannot guarantee regulatory compliance or legal accuracy. Ingesting source documents improves traceability with page-level citations but does not eliminate LLM hallucinations. Never treat output from this tool as definitive legal guidance.

---

## Architecture

```
React (Vite, port 5173)         Spring Boot 3.2.4 (Java 17, port 8080)       Flask AI Microservice (Python 3.13, port 5000)
       │                                         │                                           │
       │── POST /api/auth/login ───────────────► │ (JWT issuance & auth)                     │
       │── POST /api/records ──────────────────► │── POST /describe ────────────────────────►│── Pydantic v2 validation
       │                                         │── POST /categorise ──────────────────────►│── Redis cache lookup
       │── GET /api/records ───────────────────► │── POST /recommend ───────────────────────►│── ChromaDB RAG retrieval
       │── GET /api/records/{id}/recommendations►│── POST /generate-report ────────────────►│── Context injection
       │── GET /api/records/{id}/report ───────►│                                           │── Groq LLM call
       │── GET /api/records/export (CSV) ──────►│                                           │── Pydantic response validation
       │                                         │                                           │── Redis cache write
       │◄── Enriched JSON response ──────────────│◄──── Grounded JSON (citations, page refs)─│
                                                 │
                                        PostgreSQL 16 (compliance records)
                                        Redis 7 (5-factor cached AI results)
                                        ChromaDB (embedded 232-chunk vector store)
```

### Services Overview

| Service | Technology | Port | Containerized in Compose? |
|---------|-----------|------|---------------------------|
| **Frontend** | React 18 + Vite | 5173 (dev) | **No** (runs separately on host via `npm run dev`) |
| **Backend** | Spring Boot 3.2.4 / Java 17 | 8080 | **Yes** (`backend` service) |
| **AI Microservice** | Python 3.13 / Flask | 5000 | **Yes** (`ai-service` service) |
| **Database** | PostgreSQL 16 | 5432 | **Yes** (`postgres` service) |
| **Cache** | Redis 7 | 6379 | **Yes** (`redis` service) |
| **Vector Store** | ChromaDB (embedded) | — | **Yes** (persisted under `chromadata` volume) |

> **Containerization Scope:** Docker Compose runs only **PostgreSQL, Redis, the Flask AI microservice, and the Spring Boot backend**. The React frontend is run separately on the host machine.

---

## API Endpoints

### Spring Boot Backend (`http://localhost:8080`)

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| `POST` | `/api/auth/signup` | Public | Register a new user |
| `POST` | `/api/auth/login` | Public | Authenticate user and receive JWT |
| `POST` | `/api/records` | Authenticated | Submit raw compliance text (enriches asynchronously via AI service) |
| `GET` | `/api/records` | Authenticated | List records (users see only their own; admins see all) |
| `GET` | `/api/records/{id}/recommendations` | Owner or Admin | Fetch AI-generated recommendations for a record |
| `GET` | `/api/records/{id}/report` | Owner or Admin | Generate executive audit report for a record |
| `GET` | `/api/records/export` | **Admin Only** | Export all compliance records as a CSV audit log |

### Flask AI Microservice (`http://localhost:5000`)

| Method | Endpoint | Request Model | Response Model | Description |
|--------|----------|---------------|----------------|-------------|
| `POST` | `/describe` | `DescribeRequest` | `DescribeResponse` | Professional compliance rewriting with RAG context |
| `POST` | `/categorise` | `CategoriseRequest` | `CategoriseResponse` | DPDP category classification with confidence score |
| `POST` | `/recommend` | `RecommendRequest` | `RecommendResponse` | Actionable compliance recommendations |
| `POST` | `/generate-report` | `GenerateReportRequest` | `GenerateReportResponse` | Comprehensive executive summary and audit report |
| `GET` | `/health` | — | JSON | Health status, uptime, ChromaDB chunk count, Redis connectivity |

---

## Request Flow (End-to-End)

1. **User Authentication**: Client submits credentials to `POST /api/auth/login`. Spring Boot verifies credentials and issues a signed JWT containing user identity and roles (`ROLE_USER` or `ROLE_ADMIN`).
2. **Submission**: Client submits compliance text to `POST /api/records` with `Authorization: Bearer <token>`.
3. **Persistence & Asynchronous Hand-off**:
   - `ComplianceController` validates the JWT and creates a `ComplianceRecord` in PostgreSQL with status `PENDING`.
   - `AsyncEnricher` (a dedicated Spring `@Component` that ensures CGLIB proxy interception) executes in a background thread pool, calling `POST http://ai-service:5000/describe`.
4. **AI Microservice Pipeline**:
   - **Pydantic Validation**: Validates payload structure (non-empty, non-whitespace, $\le 5000$ chars).
   - **Redis Cache Check**: Generates a 5-factor key (`endpoint + normalized_input + prompt_hash + model_id + manifest_hash + rag_settings`). Returns cached response immediately on hit.
   - **ChromaDB Vector Retrieval**: Embeds text using `all-MiniLM-L6-v2` and queries the 232-chunk vector store with cosine distance ranking.
   - **Prompt Injection**: Injects authoritative legal context passages and section markers into prompt templates.
   - **Groq LLM Execution**: Calls `llama-3.3-70b-versatile` with low temperature ($0.1$ to $0.3$).
   - **Response Validation**: Enforces Pydantic response models and attaches verified chunk citations with page numbers.
   - **Cache Write**: Stores the validated response in Redis with TTL ($3600$s).
5. **Enrichment & Dashboard Display**: `AsyncEnricher` updates the database record with the generated description and transitions status to `COMPLETED`. The React UI displays the record with an informational AI disclaimer badge.

---

## Knowledge Base & Document Ingestion

The active ChromaDB knowledge base contains **232 chunks** extracted from the two Gazette PDF publications located in `ai-service/documents/`:

1. **`DPDP_ACT_2023.pdf`** (The Digital Personal Data Protection Act, 2023 — Act No. 22 of 2023):
   - 21 pages, 63,482 characters $\to$ **115 chunks**
   - Covers Chapters I–IX (Sections 1–44) and the Penalties Schedule.
2. **`DPDP_Rules_2025_English_only.pdf`** (Digital Personal Data Protection Rules, 2025 — G.S.R. 846(E)):
   - 18 pages, 63,100 characters $\to$ **117 chunks**
   - Covers Rules 1–23 and First/Second Schedules.

Metadata and verification status are recorded in [`ai-service/documents/corpus_manifest.json`](file:///e:/dpdp_Gravity/ai-service/documents/corpus_manifest.json).

> **Provenance Notice:** Ingestion does not prove legal authenticity. Local PDFs are registered with `source_authority_status: "unverified_local_file"` until official publication URLs (such as `egazette.gov.in`) are independently confirmed.

### Ingestion Instructions

#### Ingesting PDF Files
PDF extraction requires `pypdf`:
```bash
cd ai-service
python ingest_documents.py
```
The PDF ingestion engine:
- Extracts digital text page-by-page, preserving document page numbers ($1$-indexed).
- Detects chapters, sections, and rule headings.
- Strips repeated Gazette publication headers and footers without modifying clause text, punctuation, or statutory numbering.
- Chunks text into paragraph-aware blocks ($\approx 700$ chars with $100$-char overlap).
- Embeds using `sentence-transformers/all-MiniLM-L6-v2`.
- Assigns deterministic chunk IDs: `{doc_id}_p{page_num}_c{chunk_index}`.

#### Ingesting TXT / MD Files
Plain text (`.txt`) and Markdown (`.md`) files placed in `ai-service/documents/` are chunked by paragraph and assigned page number $1$:
```bash
cd ai-service
python ingest_documents.py
```

#### Verification Command
Verify the total number of chunks stored in ChromaDB:
```bash
python -c "from services.chroma_client import ChromaClient; c = ChromaClient(); print(c.count(), 'chunks stored | Version:', c.get_corpus_version())"
```

#### Idempotency
Rerunning `python ingest_documents.py` is **fully idempotent**:
- Existing chunks for re-indexed documents are purged prior to upsert.
- Unchanged documents retain stable chunk IDs without creating duplicates.
- To completely wipe and rebuild the ChromaDB collection from scratch:
  ```bash
  python ingest_documents.py --reset
  ```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in real values before starting services:

### Required Variables

| Variable | Service | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | AI service | Groq Cloud API key (obtain from console.groq.com/keys) |
| `JWT_SECRET` | Backend | Base64-encoded $\ge 256$-bit HMAC key for signing JWTs |
| `DB_PASSWORD` | Backend / Postgres | PostgreSQL database password |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8080` | Frontend $\to$ backend base URL |
| `AI_SERVICE_URL` | `http://localhost:5000` | Backend $\to$ AI service URL (`http://ai-service:5000` in Compose) |
| `REDIS_HOST` | `localhost` | Redis hostname (`redis` in Compose) |
| `REDIS_PORT` | `6379` | Redis port |
| `ENABLE_CACHE` | `true` | Enable or disable Redis caching |
| `CACHE_TTL_SECONDS` | `3600` | Redis cache TTL in seconds |
| `CHROMA_DATA_DIR` | `<ai-service>/chroma_data` | ChromaDB persistent storage directory |
| `CHROMA_TOP_K` | `3` | Number of context chunks retrieved per query |
| `CHROMA_MAX_DISTANCE` | *(disabled)* | Cosine distance threshold for filtering irrelevant chunks |
| `REQUIRE_GROUNDING` | `false` | If `true`, returns 422 error if no context is retrieved |

Generate a secure JWT secret:
```bash
python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
```

---

## Local Development Setup

### Prerequisites

- **Java 17**, Maven 3.9+
- **Python 3.13** (with `pip`)
- **Node.js 20+**, npm
- **PostgreSQL 16** (or use Docker Compose for the database)
- **Redis 7** (or use Docker Compose for the cache)

### 1. AI Microservice (Flask)

```bash
cd ai-service
pip install -r requirements.txt
set GROQ_API_KEY=your_key_here
set REDIS_HOST=localhost
python app.py
# Health check: curl http://localhost:5000/health
```

### 2. Backend (Spring Boot 3.2.4 / Java 17)

```bash
cd dpdp
mvn spring-boot:run
# Backend will bind to http://localhost:8080
```

### 3. Frontend (React 18 + Vite)

```bash
cd frontend
npm install
npm run dev
# Access the web UI at http://localhost:5173
```

---

## Docker Compose Deployment

Docker Compose starts **PostgreSQL 16, Redis 7, the Flask AI microservice, and the Spring Boot backend**:

```bash
# 1. Create and populate .env
cp .env.example .env

# 2. Build and start containers
docker-compose up --build

# 3. Access endpoints:
#   Backend:    http://localhost:8080
#   AI Service: http://localhost:5000/health
#   Postgres:   localhost:5432
#   Redis:      localhost:6379
```

> The React frontend is run on the host via `npm run dev` in the `frontend/` directory.

### Persistent Volumes

| Volume | Mount Path | Purpose |
|--------|------------|---------|
| `pgdata` | `/var/lib/postgresql/data` | PostgreSQL tables and compliance records |
| `redisdata` | `/data` | Redis AOF cache data |
| `chromadata` | `/app/chroma_data` | ChromaDB vector embeddings and chunk metadata |

---

## Automated Test Execution

### AI Microservice (Python — 40 tests)

```powershell
$env:PYTHONPATH="e:\dpdp_Gravity\ai-service"
python -m pytest e:\dpdp_Gravity\ai-service\tests -v
```

**Result:** `40 passed` (all external dependencies mocked; requires no live API keys or network access).

Test suite covers:
- RAG retrieval, context injection, and page-aware citation validation.
- PDF discovery, manifest hash verification, section extraction, and image-only PDF detection.
- Error handling for encrypted, corrupt, and empty PDFs.
- Idempotent ingestion and stale chunk deletion logic.
- Cache key invalidation upon manifest, corpus hash, prompt, or RAG parameter changes.
- Pydantic validation across all 4 endpoints (empty, whitespace, length $>5000$, extra fields).
- Redis cache hit, miss, and outage graceful degradation.
- Empty collection handling and ChromaDB unavailable fallback.

### Spring Boot Backend (Java 17 — 7 tests)

```powershell
mvn -f dpdp/pom.xml test
```

**Result:** `7 passed` (`DpdpApplicationTests`: 1, `ComplianceServiceTest`: 6).

### Frontend Production Build

```powershell
cd frontend; npm run build
```

**Result:** Clean Vite production build.

---

## Benchmarks & Performance Metrics

Benchmark scripts are in `benchmarks/`.

### 1. Redis Cache Overhead Benchmark (Mocked / Offline)

```bash
python benchmarks/benchmark_cache.py --samples 25
```

- **Methodology**: Deterministic offline benchmark measuring cache lookup overhead against a simulated 250 ms AI delay with an in-memory Redis mock.
- **Measured Result**:
  - Uncached p50: 253.62 ms
  - Cached p50: 1.38 ms
  - Latency reduction: **99.46%** (183.78× speedup)
- **Notice**: This benchmark isolates caching layer overhead. It does not measure live Groq API latency.

### 2. RAG Retrieval & Citation Grounding Evaluation

```bash
python benchmarks/eval_grounded.py
```

- **Methodology**: Evaluates 5 reviewed compliance scenarios against the 232 active legal chunks in ChromaDB.
- **Measured Result**:
  - Active Chunks in ChromaDB: **232 chunks**
  - Retrieval Coverage: **100%** (5/5 queries retrieved relevant candidate passages)
  - Citation Verification: **15/15 citations verified** against active chunk IDs in ChromaDB
  - Invalid Citation Rate: **0.0%**
- **Notice**: "Retrieval coverage" measures vector matching against the local corpus. It does **not** guarantee legal accuracy or correctness of the generated advice.

### 3. Application Cold Start Measurement

```bash
python benchmarks/measure_setup.py
```

- **Measured Startup**: **30.175 seconds** total cold init on Windows 11 (SentenceTransformer model loading: 17.01s, Redis timeout check: 12.51s, web assembly: 0.64s).

---

## Project Structure

```
dpdp_Gravity/
├── ai-service/
│   ├── app.py                     # Flask application factory
│   ├── schemas.py                 # Pydantic v2 request/response schemas with page/hash fields
│   ├── ingest_documents.py        # PDF & document extraction engine with idempotent upsert
│   ├── requirements.txt           # Python dependencies (pydantic, pypdf, chromadb, etc.)
│   ├── documents/
│   │   ├── corpus_manifest.json   # Ingested PDF corpus manifest and checksums
│   │   ├── DPDP_ACT_2023.pdf      # 2023 Act Gazette publication (21 pages, 115 chunks)
│   │   ├── DPDP_Rules_2025_English_only.pdf # 2025 Rules Gazette notification (18 pages, 117 chunks)
│   │   └── README.md              # Document ingestion and provenance guide
│   ├── chroma_data/               # Persistent ChromaDB vector storage (232 chunks)
│   ├── prompts/                   # Prompt templates ({user_input} + {context_block})
│   ├── routes/
│   │   ├── describe.py            # RAG + Pydantic + Redis caching
│   │   ├── categorise.py          # RAG + Pydantic + Redis caching
│   │   ├── recommend.py           # RAG + Pydantic + Redis caching
│   │   └── generate_report.py     # RAG + Pydantic + Redis caching
│   ├── services/
│   │   ├── chroma_client.py       # ChromaDB client with manifest versioning
│   │   ├── rag_service.py         # RAG orchestration and citation extraction
│   │   ├── cache_service.py       # 5-factor Redis key computation & fallback
│   │   └── groq_client.py         # Groq API client
│   └── tests/
│       └── test_app.py            # 40 automated tests (mocks all external services)
├── dpdp/                          # Spring Boot 3.2.4 Backend (Java 17)
│   ├── pom.xml                    # Maven dependencies (Java 17, Spring Boot 3.2.4)
│   ├── Dockerfile                 # eclipse-temurin:17-jdk-alpine
│   └── src/main/java/com/campuspe/dpdp/
│       ├── controller/            # ComplianceController, AuthController
│       ├── service/               # ComplianceService, AsyncEnricher, AiServiceClient
│       └── security/              # SecurityConfig, JwtAuthFilter, JwtUtils
├── frontend/                      # React 18 + Vite Web Application
├── benchmarks/
│   ├── benchmark_cache.py         # Offline cache latency benchmark
│   ├── benchmark_throughput.py    # Opt-in live Groq throughput benchmark
│   ├── eval_grounded.py           # RAG retrieval & citation evaluation harness
│   └── measure_setup.py           # Startup latency measurement
├── docker-compose.yml             # Postgres + Redis + AI service + Backend
├── .env.example                   # Safe environment variable template
├── SECURITY.md                    # Server-side security and authorization policy
└── README.md
```
