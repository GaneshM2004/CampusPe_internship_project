# DPDP Act Compliance Centre

An AI-powered compliance platform built during my internship at **CampusPe**, designed to help organizations navigate India's **Digital Personal Data Protection (DPDP) Act, 2023**, the Indian equivalent of GDPR.

The platform automates data protection auditing, generates compliance recommendations, and produces executive-level audit reports using a RAG-based AI pipeline backed by Groq's Llama-3.3-70b model.

---

## What Problem It Solves

India's DPDP Act places strict obligations on organizations that handle personal data. Compliance is complex, legal-heavy, and expensive to audit manually. This platform lets organizations upload or describe their data handling practices, get instant AI-generated compliance gap analysis, receive actionable recommendations mapped to DPDP Act provisions, and download structured audit reports ready for DPO (Data Protection Officer) review.

---

## Architecture

A 3-tier microservice architecture with a dedicated AI service, separating concerns cleanly across frontend, backend, and ML layers.

```
[ React 18 + Vite Frontend ]
          |
          v
[ Spring Boot 3.x Backend ] <---> [ PostgreSQL 15 ]
          |                              |
          v                              +--> [ Redis 7 Cache ]
[ Flask AI Microservice ]
          |
          +---> [ Groq Cloud API — Llama-3.3-70b ]
          +---> [ ChromaDB Vector Store (RAG) ]
```

All services are containerized and orchestrated via Docker Compose.

---

## Features

- AI compliance auditing with automated gap analysis against DPDP Act provisions
- RAG pipeline using ChromaDB and sentence-transformers for context-aware responses
- Full audit report generation with executive summaries and findings
- Compliance categorization that auto-classifies inputs into DPDP categories
- DPO summary generator that converts raw compliance data into professional summaries
- Real-time analytics dashboard built with Recharts
- JWT authentication with Spring Security
- Swagger API documentation

---

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Axios, Recharts |
| Backend | Java 17, Spring Boot 3.x, Spring Security, JWT, Flyway |
| Database | PostgreSQL 15, Redis 7 |
| AI Service | Python 3.11, Flask 3.x, Groq API (Llama-3.3-70b) |
| AI / ML | ChromaDB, sentence-transformers, RAG pipeline |
| Infrastructure | Docker, Docker Compose |

---

## Getting Started

### Prerequisites
- Docker and Docker Compose
- A free [Groq API key](https://console.groq.com)

### 1. Clone the repo

```bash
git clone https://github.com/GaneshM2004/CampusPe_internship_project.git
cd CampusPe_internship_project
```

### 2. Set up environment variables

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=gsk_xxxx...
DB_PASSWORD=postgres
JWT_SECRET=your_secret_key_here
VITE_API_URL=http://localhost:8080
```

### 3. Start all services

```bash
docker-compose up --build
```

### 4. Access the app

| Service | URL |
|---|---|
| Frontend | http://localhost |
| Swagger API Docs | http://localhost:8080/swagger-ui.html |
| AI Service Health | http://localhost:5000/health |

---

## AI Service API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/describe` | POST | Generates professional DPO summaries from raw input |
| `/recommend` | POST | Returns 3 actionable compliance recommendations as JSON |
| `/generate-report` | POST | Produces a full audit report with executive summary and findings |
| `/categorise` | POST | Classifies input into DPDP compliance categories |
| `/health` | GET | Returns model uptime, model name, and ChromaDB stats |

---

## Project Structure

```
frontend/           React 18 + Vite app (dashboard, analytics, forms)
dpdp/               Spring Boot backend (auth, APIs, DB migrations)
ai-service/         Flask AI microservice (Groq, ChromaDB, RAG)
docker-compose.yml  Orchestrates all services
.env                Environment config (not committed)
```

---

## Security

JWT-based stateless authentication is handled via Spring Security. Passwords are hashed and secrets are managed through environment variables. See [SECURITY.md](./SECURITY.md) for the responsible disclosure policy.

---

## Built At

This was built as part of my internship at **CampusPe** as a production-grade MVP demonstrating AI-assisted legal compliance tooling for the Indian market.
