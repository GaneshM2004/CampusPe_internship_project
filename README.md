# Tool-15: DPDP Act Compliance Centre

## 1. Project Overview

The **DPDP Act Compliance Centre** is an AI-powered MVP designed to assist organizations in navigating the India **Digital Personal Data Protection (DPDP) Act**.

This real-world application uses an industry-standard tech stack to provide automated data protection auditing, compliance recommendations, and AI-generated reports.

---

## 2. System Architecture

This project follows a **3-tier microservice architecture** to ensure scalability and separation of concerns.

```text
      [ React 18 + Vite Frontend ]
                | (Port 80)
                v
      [ Spring Boot 3.x Backend ] <---> [ PostgreSQL 15 ]
                | (Port 8080)              |
                v                          +--> [ Redis 7 Cache ]
      [ Flask 3.x AI Microservice ]
                | (Port 5000)
                +---> [ Groq Cloud API (Llama-3.3-70b) ]
                +---> [ ChromaDB Vector Store ]
```

---

## 3. Tech Stack

### Backend
- Java 17
- Spring Boot 3.x
- Spring Security + JWT
- Flyway
- PostgreSQL 15
- Redis 7

### AI Service
- Python 3.11
- Flask 3.x
- Groq API (Llama-3.3-70b)
- ChromaDB
- sentence-transformers

### Frontend
- React 18+
- Vite
- Tailwind CSS
- Axios
- Recharts

### Infrastructure
- Docker
- Docker Compose

---

## 4. Environment Variables

Create a `.env` file in the project root directory.

### Required Variables

| Variable | Description | Example |
|----------|-------------|----------|
| `GROQ_API_KEY` | API key from Groq Cloud | `gsk_xxxx...` |
| `DB_PASSWORD` | PostgreSQL password | `postgres` |
| `JWT_SECRET` | Secret key for JWT token signing | `your_secret_key` |
| `VITE_API_URL` | Frontend URL for backend access | `http://localhost:8080` |

---

## 5. Setup & Installation

### 1. Clone the Repository

```bash
git clone [repository-url]
cd your-project-folder
```

### 2. Configure Environment

Create a `.env` file in the root directory and add your credentials:

```env
GROQ_API_KEY=gsk_xxxx...
DB_PASSWORD=postgres
JWT_SECRET=your_secret_key
VITE_API_URL=http://localhost:8080
```

### 3. Start Services

Build and start all containers using Docker Compose:

```bash
docker-compose up --build
```

---

## 6. Access the Application

| Service | URL |
|---------|-----|
| Frontend | `http://localhost` |
| Swagger API Docs | `http://localhost:8080/swagger-ui.html` |
| AI Health Check | `http://localhost:5000/health` |

---

## 7. API Reference (AI Microservice)

### `POST /describe`
Generates professional DPO summaries based on raw input.

### `POST /recommend`
Returns 3 actionable compliance recommendations as a JSON array.

### `POST /generate-report`
Produces a full audit report including executive summaries and findings.

### `POST /categorise`
Classifies inputs into predefined compliance categories.

### `GET /health`
Returns:
- Model uptime
- Model name
- ChromaDB statistics

---

## 8. Folder Structure

```text
backend/
 ├── controllers/
 ├── services/
 ├── migrations/
 └── ...

ai-service/
 ├── routes/
 ├── groq-client/
 ├── chromadb-services/
 ├── rag-prompts/
 └── ...

frontend/
 ├── components/
 ├── pages/
 ├── analytics/
 ├── dashboard/
 └── ...
```

---

## 9. Features

- AI-powered compliance auditing
- Automated DPDP Act recommendations
- Executive audit report generation
- Compliance categorization system
- JWT-based authentication
- Vector search with ChromaDB
- Real-time analytics dashboard
- Dockerized microservice deployment

---
