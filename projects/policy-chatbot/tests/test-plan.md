# Test Plan: Policy Chatbot

> **Version:** 1.0
> **Status:** Draft
> **Date:** 2026-03-20
> **Produced by:** Test Agent
> **Input sources:**
> - `projects/policy-chatbot/requirements/requirements.md`
> - `projects/policy-chatbot/requirements/user-stories.md`
> - `projects/policy-chatbot/design/wireframe-spec.md`

---

## 1. Scope

### In Scope
- RAG pipeline core logic (intent classification, confidential topic detection, answer
  orchestration, no-match handling, fallback behavior)
- Authentication and authorization (JWT validation, role-based access control)
- All 22 API endpoints defined in the wireframe spec
- Auth boundary tests (401 unauthenticated, 403 insufficient role)
- Error paths (404 not found, 409 conflict, 422 validation errors, 502 upstream failure)
- Feedback submission and duplicate prevention
- Admin document lifecycle (create, update, patch/retire, reindex)
- Analytics endpoints (summary, top intents, unanswered queries, flagged topics)
- Coverage report endpoint
- Admin test-query preview
- Conversation history listing and detail retrieval (ownership enforcement)
- User profile retrieval

### Out of Scope
- End-to-end tests against live Azure services (requires infrastructure)
- Load/performance tests (deferred — Locust scripts will be added when NFR targets are baselined)
- Microsoft Teams bot integration testing (external channel)
- Real LLM response quality evaluation (mocked in tests)
- Database migration testing (Alembic migrations tested separately)

---

## 2. Test Strategy

| Test Type | Scope | Framework | Coverage Target |
|-----------|-------|-----------|-----------------|
| Unit | Core business logic (`app/core/`) | pytest + pytest-asyncio | 80% line coverage |
| Integration | API endpoints + mocked DB/services | pytest + httpx AsyncClient | All 22 endpoints |
| Contract | OpenAPI spec conformance | manual review (future: schemathesis) | All endpoints |

---

## 3. Requirements Coverage Matrix

| Requirement | Test Type | Test ID | Description | Status |
|-------------|-----------|---------|-------------|--------|
| FR-001 | Integration | IT-DOC-001 | Upload new policy document via admin API | Planned |
| FR-002 | Integration | IT-DOC-001 | Document upload validates supported file types (PDF, DOCX, HTML) | Planned |
| FR-003 | Integration | IT-DOC-001 | Uploaded document triggers indexing | Planned |
| FR-004 | Integration | IT-DOC-001 | Document metadata stored (title, category, effective date, owner) | Planned |
| FR-005 | Integration | IT-DOC-004 | Re-index single document | Planned |
| FR-005 | Integration | IT-DOC-005 | Re-index full corpus | Planned |
| FR-006 | Integration | IT-DOC-002 | Document detail includes version history | Planned |
| FR-007 | Integration | IT-CHAT-001 | Accept natural language question via POST /v1/chat | Planned |
| FR-008 | Unit | UT-RAG-003 | Intent classification via RAG pipeline | Planned |
| FR-009 | Unit | UT-RAG-004 | Conversation context loaded from Redis for follow-up | Planned |
| FR-010 | — | — | Concurrency target (load test, deferred) | Deferred |
| FR-011 | Integration | IT-PROF-001 | User profile with first name, department, location | Planned |
| FR-012 | Unit | UT-RAG-003 | Grounded answer generation from policy chunks | Planned |
| FR-013 | Unit | UT-RAG-003 | Response includes citations | Planned |
| FR-014 | Unit | UT-RAG-005 | No-match scenario returns appropriate response | Planned |
| FR-015 | Integration | IT-CHAT-001 | Disclaimer included in every chat response | Planned |
| FR-016 | Unit | UT-RAG-001 | Confidential topic detection (harassment, discrimination, whistleblower) | Planned |
| FR-016 | Unit | UT-RAG-002 | Confidential topic returns escalation, not answer | Planned |
| FR-017 | Integration | IT-CHAT-001 | Checklist response type for procedural queries | Planned |
| FR-018 | Integration | IT-CHAT-001 | Checklist steps classified as assisted/manual | Planned |
| FR-019 | Integration | IT-CHAT-001 | Assisted steps include actionable assistance | Planned |
| FR-020 | Integration | IT-CHAT-001 | Manual steps clearly state required action | Planned |
| FR-021 | Integration | IT-CHAT-001 | Follow-up on checklist step | Planned |
| FR-022 | Integration | IT-CHAT-001 | Wayfinding info in response | Planned |
| FR-023 | Integration | IT-CHAT-001 | Wayfinding fallback when data unavailable | Planned |
| FR-024 | Integration | IT-CHAT-001 | Campus map URL in wayfinding response | Planned |
| FR-025 | Integration | IT-ESC-001 | Explicit escalation to live agent | Planned |
| FR-026 | Integration | IT-ESC-001 | Conversation transcript passed to ServiceNow | Planned |
| FR-027 | Unit | UT-RAG-005 | Auto-escalation offer after low-confidence answers | Planned |
| FR-028 | Integration | IT-FB-001 | Submit thumbs-up/thumbs-down feedback | Planned |
| FR-029 | Integration | IT-ANA-001 | Analytics summary (volume, resolution rate, escalation rate) | Planned |
| FR-029 | Integration | IT-ANA-002 | Top intents endpoint | Planned |
| FR-029 | Integration | IT-ANA-003 | Unanswered queries log | Planned |
| FR-030 | Integration | IT-ANA-004 | Flagged topics from negative feedback | Planned |
| FR-031 | Integration | IT-DOC-001 | Admin document management (create, list, update, retire) | Planned |
| FR-032 | Integration | IT-TQ-001 | Admin test-query preview | Planned |
| FR-033 | Integration | IT-COV-001 | Policy coverage report by domain | Planned |

---

## 4. User Story Acceptance Criteria Coverage

| Story | Acceptance Criterion | Test ID |
|-------|---------------------|---------|
| US-001 | Question with matching policy returns cited answer | IT-CHAT-001, UT-RAG-003 |
| US-001 | Question with no match returns fallback + escalation offer | UT-RAG-005 |
| US-001 | Disclaimer included in every response | IT-CHAT-001 |
| US-002 | Follow-up question uses prior conversation context | UT-RAG-004 |
| US-002 | New topic within same session handled correctly | UT-RAG-004 |
| US-003 | Procedural query generates numbered checklist | IT-CHAT-001 |
| US-003 | Assisted step offers actionable help | IT-CHAT-001 |
| US-003 | Manual step states required action clearly | IT-CHAT-001 |
| US-003 | Detail on specific checklist step | IT-CHAT-001 |
| US-004 | Wayfinding available — campus map link returned | IT-CHAT-001 |
| US-004 | Wayfinding unavailable — fallback to building/room | IT-CHAT-001 |
| US-005 | Explicit escalation request creates ServiceNow ticket | IT-ESC-001 |
| US-005 | Alternative phrasing recognized as escalation | IT-ESC-001 |
| US-005 | Automatic escalation after low confidence | UT-RAG-005 |
| US-005 | Conversation transcript preserved | IT-ESC-001 |
| US-006 | Harassment query triggers confidential escalation | UT-RAG-001, UT-RAG-002 |
| US-006 | Discrimination/whistleblower detected | UT-RAG-001 |
| US-006 | General question about sensitive area NOT escalated | UT-RAG-001 |
| US-007 | Positive feedback recorded | IT-FB-001 |
| US-007 | Negative feedback with comment recorded | IT-FB-002 |
| US-007 | Duplicate feedback returns 409 | IT-FB-003 |
| US-007 | Feedback optional (skip allowed) | IT-FB-001 |
| US-008 | Upload new PDF document | IT-DOC-001 |
| US-008 | Re-index existing document | IT-DOC-004 |
| US-008 | Retire outdated document | IT-DOC-003 |
| US-008 | Full corpus re-index | IT-DOC-005 |
| US-009 | Test query returns live answer | IT-TQ-001 |
| US-009 | Test query with draft document shows preview | IT-TQ-002 |
| US-010 | Query volume metrics displayed | IT-ANA-001 |
| US-010 | Resolution and escalation rates | IT-ANA-001 |
| US-010 | Unanswered query log | IT-ANA-003 |
| US-010 | Flagged negative feedback topics | IT-ANA-004 |
| US-011 | Greeting by first name (profile endpoint) | IT-PROF-001 |
| US-011 | Role-aware profile data available | IT-PROF-001 |
| US-012 | Coverage report by category | IT-COV-001 |
| US-012 | Categories with zero docs shown as gaps | IT-COV-001 |

---

## 5. Test Scenarios

### TS-001: Confidential Topic Detection

- **Requirement:** FR-016
- **Type:** Unit
- **Preconditions:** None
- **Steps:**
  1. Call `detect_confidential_topic("I want to report harassment")`
  2. Call `detect_confidential_topic("What is the PTO policy?")`
- **Expected Result:** Returns True for harassment, False for PTO
- **Pass/Fail Criteria:** Boolean return matches expected value

### TS-002: RAG Orchestration — Standard Answer

- **Requirement:** FR-008, FR-012, FR-013
- **Type:** Unit
- **Preconditions:** Mocked search, OpenAI, Redis services
- **Steps:**
  1. Call `orchestrate_chat` with a non-confidential message
  2. Verify search.hybrid_search called
  3. Verify openai.generate_answer called
- **Expected Result:** Returns answer with citations and intent
- **Pass/Fail Criteria:** response_type == "answer"

### TS-003: RAG Orchestration — No Match

- **Requirement:** FR-014, FR-027
- **Type:** Unit
- **Preconditions:** Search returns empty results, intent confidence < 0.5
- **Steps:**
  1. Call `orchestrate_chat` with a query that matches no policy
- **Expected Result:** Returns no_match response with escalation suggestion
- **Pass/Fail Criteria:** response_type == "no_match"

### TS-004: RAG Orchestration — OpenAI Failure Fallback

- **Requirement:** NFR-006
- **Type:** Unit
- **Preconditions:** Search returns chunks, OpenAI raises exception
- **Steps:**
  1. Call `orchestrate_chat` where openai.generate_answer raises Exception
- **Expected Result:** Returns fallback_search with basic search results
- **Pass/Fail Criteria:** response_type == "fallback_search"

### TS-005: Chat Endpoint — Happy Path

- **Requirement:** FR-007, FR-015
- **Type:** Integration
- **Preconditions:** Authenticated user, mocked RAG pipeline
- **Steps:**
  1. POST /v1/chat with valid message
- **Expected Result:** 200 with conversation_id, message_id, response with disclaimer
- **Pass/Fail Criteria:** Status 200, disclaimer present

### TS-006: Chat Endpoint — Unauthenticated

- **Requirement:** Security
- **Type:** Integration
- **Steps:**
  1. POST /v1/chat without Authorization header
- **Expected Result:** 401 Unauthorized
- **Pass/Fail Criteria:** Status 401

### TS-007: Escalation Endpoint

- **Requirement:** FR-025, FR-026
- **Type:** Integration
- **Preconditions:** Existing conversation owned by user
- **Steps:**
  1. POST /v1/chat/escalate with valid conversation_id
- **Expected Result:** 200 with ticket_id from ServiceNow
- **Pass/Fail Criteria:** Response includes ticket_id and status "initiated"

### TS-008: Feedback — Duplicate Prevention

- **Requirement:** FR-028
- **Type:** Integration
- **Preconditions:** Feedback already exists for message
- **Steps:**
  1. POST /v1/feedback with same message_id twice
- **Expected Result:** First returns 201, second returns 409
- **Pass/Fail Criteria:** Correct status codes

### TS-009: Admin Document Upload

- **Requirement:** FR-001, FR-031
- **Type:** Integration
- **Preconditions:** Admin role
- **Steps:**
  1. POST /v1/admin/documents with multipart form data
- **Expected Result:** 201 with document metadata and indexing_status
- **Pass/Fail Criteria:** Status 201, indexing_status == "in_progress"

### TS-010: Admin Document Upload — Employee Forbidden

- **Requirement:** Security
- **Type:** Integration
- **Preconditions:** Employee role (not admin)
- **Steps:**
  1. POST /v1/admin/documents with Employee token
- **Expected Result:** 403 Forbidden
- **Pass/Fail Criteria:** Status 403

---

## 6. Auth & Security Test Cases

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| SEC-001 | Unauthenticated request to POST /v1/chat | 401 Unauthorized |
| SEC-002 | Unauthenticated request to POST /v1/feedback | 401 Unauthorized |
| SEC-003 | Employee accessing admin endpoint (GET /v1/admin/documents) | 403 Forbidden |
| SEC-004 | Employee accessing another user's conversation | 403 Forbidden |
| SEC-005 | Conversation not found returns 404 (not data leak) | 404 Not Found |
| SEC-006 | Unauthenticated request to GET /v1/admin/analytics/summary | 401 Unauthorized |

---

## 7. Error Path Test Cases

| Test ID | Scenario | Expected Behavior |
|---------|----------|-------------------|
| ERR-001 | POST /v1/chat with empty message | 422 Validation Error |
| ERR-002 | POST /v1/chat with message > 2000 chars | 422 Validation Error |
| ERR-003 | POST /v1/chat/escalate with non-existent conversation | 404 Not Found |
| ERR-004 | POST /v1/feedback with invalid rating value | 422 Validation Error |
| ERR-005 | POST /v1/feedback for non-existent message | 404 Not Found |
| ERR-006 | POST /v1/admin/documents with unsupported file type | 400 Bad Request |
| ERR-007 | POST /v1/admin/documents with invalid category | 400 Bad Request |
| ERR-008 | POST /v1/admin/documents with duplicate title | 409 Conflict |
| ERR-009 | PATCH /v1/admin/documents/{id} with invalid status | 400 Bad Request |
| ERR-010 | GET /v1/admin/documents/{id} for non-existent doc | 404 Not Found |
| ERR-011 | POST /v1/admin/test-query with draft_document_id not found | 404 Not Found |

---

## 8. Test Environment

| Component | Details |
|-----------|---------|
| Runtime | Python 3.11+ |
| Test framework | pytest + pytest-asyncio |
| HTTP client | httpx AsyncClient with ASGITransport |
| Database | Mocked AsyncSession (no real DB in unit/integration tests) |
| External services | All mocked (OpenAI, Search, Redis, Blob, ServiceNow, Graph) |
| CI integration | Tests run in `test` stage of CI pipeline |

---

## 9. Exit Criteria

- All unit and integration tests pass (`pytest -x -q`)
- Code coverage ≥ 80% on `app/` (`--cov=app --cov-fail-under=80`)
- No test depends on another test's state
- All FR requirements have at least one test (except FR-010 deferred to load tests)
- All user story acceptance criteria have corresponding tests
- All 22 API endpoints have integration tests
- Auth boundary tests cover 401 and 403 scenarios
