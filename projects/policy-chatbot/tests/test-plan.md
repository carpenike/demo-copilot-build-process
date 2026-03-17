# Test Plan: Policy Chatbot

> **Version:** 1.0
> **Status:** Draft
> **Date:** 2026-03-17
> **Produced by:** Test Agent
> **Input sources:**
> - `projects/policy-chatbot/requirements/requirements.md`
> - `projects/policy-chatbot/requirements/user-stories.md`
> - `projects/policy-chatbot/design/wireframe-spec.md`

---

## 1. Scope

### In Scope
- Intent classification logic (FR-008, FR-016)
- RAG pipeline orchestration: retrieval → generation → citation → checklist (FR-012–FR-021)
- Sensitive topic detection and immediate escalation (FR-016)
- Keyword fallback when LLM is unavailable (NFR-006)
- Document chunking and text extraction (FR-002, FR-003)
- All REST API endpoints defined in wireframe-spec.md:
  - Health: `GET /health`, `GET /ready`
  - Chat: `POST /api/v1/chat`, escalate, feedback
  - Admin: document CRUD, reindex, test-query, coverage, analytics, flagged topics
- Authentication and authorization (NFR-007, NFR-010)
- Error handling and RFC 7807 responses

### Out of Scope
- Bot Framework message handling (`POST /api/messages`) — third-party SDK integration
- Azure AI Search index creation (infrastructure concern)
- Azure Blob Storage upload integration (mocked in tests)
- Load/performance testing (NFR-001, NFR-010, NFR-013) — deferred to staging
- UI/accessibility testing (NFR-017, NFR-018) — no UI in this project
- Multi-language support — out of scope for v1

---

## 2. Test Strategy

| Test Type | Scope | Framework | Coverage Target |
|-----------|-------|-----------|-----------------|
| Unit | Core business logic (`core/`, `tasks/`) | pytest | 80% line coverage |
| Integration | API endpoints + dependency mocking | pytest + httpx (TestClient) | All endpoints |

---

## 3. Requirements Coverage Matrix

| Requirement | Test Type | Test ID | Description | Status |
|-------------|-----------|---------|-------------|--------|
| FR-002 | Unit | UT-001 | Text chunking preserves section headings | Planned |
| FR-003 | Unit | UT-002 | Document is chunked into semantic sections | Planned |
| FR-008 | Unit | UT-003 | Intent classifier determines domain and query type | Planned |
| FR-008 | Unit | UT-004 | Procedural vs factual classification | Planned |
| FR-012 | Unit | UT-005 | RAG pipeline retrieves chunks and generates answer | Planned |
| FR-013 | Unit | UT-006 | Response includes citations with title, section, date, URL | Planned |
| FR-014 | Unit | UT-007 | No answer when no relevant policy found | Planned |
| FR-015 | Unit | UT-008 | Standard disclaimer appended to every response | Planned |
| FR-016 | Unit | UT-009 | Sensitive topic triggers immediate escalation | Planned |
| FR-016 | Unit | UT-010 | Non-sensitive HR query handled normally | Planned |
| FR-017 | Unit | UT-011 | Procedural query generates numbered checklist | Planned |
| FR-027 | Unit | UT-012 | Auto-escalation after consecutive low-confidence answers | Planned |
| NFR-006 | Unit | UT-013 | Keyword fallback when LLM unavailable | Planned |
| FR-007 | Integration | IT-001 | POST /api/v1/chat returns cited response | Planned |
| FR-014 | Integration | IT-002 | Chat with no policy found returns appropriate message | Planned |
| FR-016 | Integration | IT-003 | Sensitive query returns escalation response | Planned |
| FR-025 | Integration | IT-004 | POST /api/v1/chat/{id}/escalate initiates escalation | Planned |
| FR-028 | Integration | IT-005 | POST /api/v1/chat/{id}/feedback records feedback | Planned |
| FR-028 | Integration | IT-006 | Duplicate feedback returns 409 | Planned |
| FR-031 | Integration | IT-007 | POST /api/admin/documents uploads document | Planned |
| FR-031 | Integration | IT-008 | POST /api/admin/documents/{id}/retire retires document | Planned |
| FR-005 | Integration | IT-009 | POST /api/admin/documents/{id}/reindex triggers reindex | Planned |
| FR-032 | Integration | IT-010 | POST /api/admin/test-query returns test results | Planned |
| FR-033 | Integration | IT-011 | GET /api/admin/coverage returns coverage report | Planned |
| FR-029 | Integration | IT-012 | GET /api/admin/analytics returns dashboard data | Planned |
| FR-030 | Integration | IT-013 | GET /api/admin/analytics/flagged returns flagged topics | Planned |
| NFR-007 | Integration | IT-014 | Unauthenticated request returns 401 | Planned |
| NFR-010 | Integration | IT-015 | Non-admin accessing admin endpoint returns 403 | Planned |
| — | Integration | IT-016 | GET /health returns 200 | Planned |
| — | Integration | IT-017 | GET /ready returns dependency status | Planned |
| — | Integration | IT-018 | POST /api/v1/chat with invalid body returns 422 | Planned |
| — | Integration | IT-019 | POST /api/v1/chat/{id}/escalate with unknown ID returns 404 | Planned |
| FR-006 | Integration | IT-020 | GET /api/admin/documents/{id}/versions returns version history | Planned |
| — | Integration | IT-021 | POST /api/admin/documents rejects unsupported format | Planned |

---

## 4. Auth & Security Test Cases

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| SEC-001 | Unauthenticated request to POST /api/v1/chat | 401 Unauthorized |
| SEC-002 | Employee (no PolicyAdmin role) accessing GET /api/admin/documents | 403 Forbidden |
| SEC-003 | Employee accessing POST /api/admin/documents | 403 Forbidden |
| SEC-004 | Admin with PolicyAdmin role accessing admin endpoints | 200 OK |

---

## 5. Error Path Test Cases

| Test ID | Scenario | Expected Behavior |
|---------|----------|-------------------|
| ERR-001 | Empty message in chat request | 422 Unprocessable Entity |
| ERR-002 | Message exceeding 2000 chars | 422 Unprocessable Entity |
| ERR-003 | Escalate with non-existent conversation ID | 404 Not Found |
| ERR-004 | Feedback on non-existent message | 400 Bad Request |
| ERR-005 | Duplicate feedback on same message | 409 Conflict |
| ERR-006 | Upload unsupported file format (.pptx) | 400 Bad Request |

---

## 6. Test Environment

| Component | Details |
|-----------|---------|
| Runtime | Python 3.11+ |
| Test framework | pytest + pytest-asyncio |
| HTTP client | httpx (FastAPI TestClient) |
| Mocking | unittest.mock (AsyncMock for async services) |
| CI Integration | Tests run in `test` stage of CI pipeline |

---

## 7. Exit Criteria

- All unit tests pass
- All integration tests pass
- Every FR has at least one corresponding test
- Every user story acceptance criterion has a corresponding test
- Auth/authz edge cases covered (401, 403)
- Error paths tested (not just happy paths)
- No test depends on another test's state
