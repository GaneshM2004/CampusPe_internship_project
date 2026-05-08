# SECURITY.md - DPDP Act Compliance Centre

## 1. Security Overview
[cite_start]This project implements a multi-layered security architecture to protect sensitive data processing logs and AI interactions[cite: 17, 73].

## 2. OWASP Top 10 Risk Mitigation
| Risk | Attack Scenario | Mitigation Strategy |
| :--- | :--- | :--- |
| **A01: Broken Access Control** | An unauthorized user attempts to delete compliance records via the API. | **Spring Security + JWT:** Implemented Role-Based Access Control (RBAC). [cite_start]Endpoints are restricted to ADMIN and MANAGER roles using `@PreAuthorize`[cite: 17, 73]. |
| **A03: Injection (SQL)** | An attacker enters malicious SQL code into the search bar to leak the database. | [cite_start]**JPA Parameterized Queries:** All database interactions use Spring Data JPA, which prevents SQL injection by treating input as data, not executable code[cite: 17, 71]. |
| **A03: Injection (AI Prompt)** | A user tries to "jailbreak" the AI to ignore DPDP rules via a specifically crafted input. | [cite_start]**Input Sanitization:** Python middleware strips HTML and detects common prompt injection patterns before sending data to Groq[cite: 71]. |
| **A04: Insecure Design** | The AI service is overwhelmed by a bot, causing a denial of service (DoS). | [cite_start]**Rate Limiting:** Implemented `flask-limiter` on the AI microservice, restricting users to $30 \text{ req/min}$[cite: 17, 71]. |
| **A07: Identification Failures** | An attacker attempts to intercept session data to impersonate a Data Protection Officer. | **Stateless JWT:** Authentication is handled via signed JSON Web Tokens. [cite_start]No session data is stored on the server[cite: 17, 71]. |

## 3. Security Sign-off
- [X] JWT Enforcement Verified
- [X] Input Sanitization Active
- [cite_start][X] Rate Limiting Confirmed [cite: 79]