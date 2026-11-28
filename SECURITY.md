# Security Policy & Architecture

This document outlines the security architecture, authentication mechanisms, and authorization controls implemented in the **DPDP Act Compliance Centre**.

---

## 1. Authentication Architecture

- **Stateless JWT Authentication:**
  - Clients authenticate via `POST /api/auth/login`.
  - Spring Boot issues an HMAC-signed JSON Web Token (`jjwt-api 0.12.6`).
  - Tokens encode the user's ID, username, and assigned role (`ROLE_USER` or `ROLE_ADMIN`).
  - All subsequent requests to `/api/records/**` must carry `Authorization: Bearer <token>`.
- **JWT Key Management:**
  - The signing secret is externalized via the `JWT_SECRET` environment variable.
  - The secret must be a base64-encoded $\ge 256$-bit key. Hardcoding secrets in source files is prohibited.
  - Default placeholder keys are restricted to local development environments.

---

## 2. Server-Side Authorization Controls

Authorization is strictly enforced in `ComplianceController.java` rather than relying on frontend role checks:

| Endpoint | Method | Required Role / Ownership | Enforcement Mechanism |
|---|---|---|---|
| `/api/auth/**` | `POST` | Public | Explicitly permitted in `SecurityConfig.java` |
| `/api/records` | `POST` | Authenticated | User identity extracted from JWT and bound to record |
| `/api/records` | `GET` | Authenticated | `ROLE_ADMIN` sees all records; `ROLE_USER` queries only records matching their user ID |
| `/api/records/{id}/recommendations` | `GET` | Owner or `ROLE_ADMIN` | `requestingUserId.equals(ownerUserId)` check; returns HTTP 403 Forbidden if mismatched |
| `/api/records/{id}/report` | `GET` | Owner or `ROLE_ADMIN` | `requestingUserId.equals(ownerUserId)` check; returns HTTP 403 Forbidden if mismatched |
| `/api/records/export` | `GET` | `ROLE_ADMIN` Only | `isAdmin(authentication)` check; returns HTTP 403 Forbidden for non-admin users |

---

## 3. Data Protection & Asynchronous State Transitions

1. **Self-Invocation Proxy Protection:**
   - Asynchronous enrichment is isolated inside `AsyncEnricher.java` (a dedicated Spring bean), preventing self-invocation proxy bypass and ensuring thread-pool execution.
2. **Deterministic State Progression:**
   - Record submission in `ComplianceService.java` immediately saves the record with `status: "PROCESSING"` and triggers `AsyncEnricher.enrichRecordWithAi(...)`.
   - On successful AI enrichment, `AsyncEnricher` sets `professionalDescription` (or a manual-review fallback string if Groq returns `null`) and transitions `status` to `"COMPLETED"`.
   - On an unhandled exception during enrichment, `AsyncEnricher` catches the error and transitions `status` to `"FAILED"`, preventing UI polling deadlocks.
3. **Safe Error Handling:**
   - Pydantic validation failures return structured error messages without exposing internal stack traces, system paths, or model credentials.
   - Redis caching suppresses and never persists error payloads or provider outages.

---

## 4. Container & Network Security

- In Docker Compose, internal communication between services (`backend` $\to$ `ai-service`, `backend` $\to$ `postgres`, `ai-service` $\to$ `redis`) utilizes isolated Docker virtual network DNS names, not `localhost`.
- Persistent storage for databases and vector embeddings is isolated in named Docker volumes (`pgdata`, `redisdata`, `chromadata`).
- Port 5432 (Postgres) and 6379 (Redis) should be bound only to localhost or unexposed in production environments.
