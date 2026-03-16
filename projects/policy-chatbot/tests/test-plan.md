# Test Plan: Policy Chatbot

> **Version:** 1.0
> **Status:** Draft
> **Date:** 2026-03-16
> **Produced by:** Test Agent
> **Input sources:**
> - `projects/policy-chatbot/requirements/requirements.md`
> - `projects/policy-chatbot/requirements/user-stories.md`
> - `projects/policy-chatbot/design/wireframe-spec.md`

---

## 1. Scope

### In Scope
- Core business logic: intent classification, document processing, RAG pipeline
- All API endpoints: health (2), chat (4), admin (10)
- Auth/authz boundary testing: unauthenticated, wrong role (Employee vs Administrator)
- Error paths: invalid input, missing resources, rate limiting
- LLM fallback mode (NFR-006)
- Confidential topic detection (FR-016)

### Out of Scope
- Frontend (web widget, admin console UI) — no frontend code exists yet
- Microsoft Teams Bot Framework integration — requires Teams test tenant
- Performance/load testing — covered by separate load test plan (future)
- End-to-end tests with real Azure services — requires staging environment
- Wayfinding API integration — depends on external Facilities API

---

## 2. Test Strategy

| Test Type | Scope | Framework | Coverage Target |
|-----------|-------|-----------|-----------------|
| Unit | Core business logic (`app/core/`) | pytest | 80% line coverage |
| Integration | API endpoints (`app/api/`) | pytest + httpx (TestClient) | All endpoints, all status codes |
| Contract | OpenAPI spec conformance | Manual verification against `openapi.yaml` | 100% of endpoints |

---

## 3. Requirements Coverage Matrix

| Requirement | Test Type | Test ID | Description | Status |
|-------------|-----------|---------|-------------|--------|
| FR-001 | Integration | IT-ADM-001 | Upload document via admin API | Planned |
| FR-002 | Unit | UT-DP-001 | Extract text from PDF preserving headings | Planned |
| FR-002 | Unit | UT-DP-002 | Extract text from DOCX preserving headings | Planned |
| FR-002 | Unit | UT-DP-003 | Extract text from HTML preserving headings | Planned |
| FR-003 | Unit | UT-DP-004 | Chunk sections into semantic chunks | Planned |
| FR-003 | Unit | UT-DP-005 | Chunks respect size limits with overlap | Planned |
| FR-004 | Integration | IT-ADM-002 | Document metadata stored on upload | Planned |
| FR-005 | Integration | IT-ADM-003 | Trigger re-indexing for single document | Planned |
| FR-005 | Integration | IT-ADM-004 | Trigger full corpus re-indexing | Planned |
| FR-006 | Integration | IT-ADM-005 | View document version history | Planned |
| FR-007 | Integration | IT-CHAT-001 | Create conversation via web channel | Planned |
| FR-007 | Integration | IT-CHAT-002 | Create conversation via teams channel | Planned |
| FR-008 | Unit | UT-IC-001 | Classify procedural query | Planned |
| FR-008 | Unit | UT-IC-002 | Classify factual query | Planned |
| FR-009 | Unit | UT-RAG-001 | Conversation history passed to LLM | Planned |
| FR-011 | Integration | IT-CHAT-003 | Greeting includes user first name | Planned |
| FR-012 | Unit | UT-RAG-002 | RAG pipeline executes hybrid search + LLM | Planned |
| FR-013 | Unit | UT-RAG-003 | Response includes citations | Planned |
| FR-014 | Unit | UT-RAG-004 | No-match response when no chunks found | Planned |
| FR-014 | Unit | UT-OAI-001 | NO_RELEVANT_POLICY token triggers no-match | Planned |
| FR-015 | Unit | UT-RAG-005 | Response includes disclaimer | Planned |
| FR-016 | Unit | UT-IC-003 | Confidential topic — harassment detected | Planned |
| FR-016 | Unit | UT-IC-004 | Confidential topic — discrimination detected | Planned |
| FR-016 | Unit | UT-IC-005 | Confidential topic — whistleblower detected | Planned |
| FR-016 | Unit | UT-RAG-006 | Confidential query bypasses RAG pipeline | Planned |
| FR-017 | Unit | UT-OAI-002 | Checklist JSON response parsed correctly | Planned |
| FR-018 | Unit | UT-OAI-003 | Checklist steps have assisted/manual type | Planned |
| FR-025 | Unit | UT-IC-006 | Escalation request — "talk to a person" | Planned |
| FR-025 | Unit | UT-IC-007 | Escalation request — "speak with someone" | Planned |
| FR-025 | Integration | IT-ESC-001 | Escalate conversation to HR | Planned |
| FR-026 | Integration | IT-ESC-002 | Escalation passes transcript to ServiceNow | Planned |
| FR-028 | Integration | IT-FB-001 | Submit positive feedback | Planned |
| FR-028 | Integration | IT-FB-002 | Submit negative feedback with comment | Planned |
| FR-029 | Integration | IT-ADM-006 | Analytics dashboard data retrieval | Planned |
| FR-030 | Integration | IT-FB-003 | Repeated negative feedback flags topic | Planned |
| FR-030 | Integration | IT-ADM-007 | View flagged topics | Planned |
| FR-031 | Integration | IT-ADM-008 | Upload document — admin only | Planned |
| FR-031 | Integration | IT-ADM-009 | Retire a document | Planned |
| FR-032 | Integration | IT-ADM-010 | Test query preview | Planned |
| FR-033 | Integration | IT-ADM-011 | Policy coverage report | Planned |
| NFR-006 | Unit | UT-RAG-007 | Keyword fallback when LLM unavailable | Planned |
| NFR-007 | Integration | IT-AUTH-001 | Unauthenticated request returns 401 | Planned |
| NFR-010 | Integration | IT-AUTH-002 | Employee cannot access admin endpoints (403) | Planned |
| NFR-010 | Integration | IT-AUTH-003 | Admin can access admin endpoints | Planned |
| NFR-010 | Integration | IT-CHAT-004 | User cannot access another user's conversation (404) | Planned |

---

## 4. Test Scenarios

### TS-001: Confidential Topic Detection
- **Requirement:** FR-016
- **Type:** Unit
- **Preconditions:** None (pure function)
- **Steps:**
  1. Call `classify_intent("I want to report harassment by my manager")`
  2. Assert result.intent == IntentResult.CONFIDENTIAL
- **Expected Result:** Intent is CONFIDENTIAL, query_type is UNKNOWN, confidence >= 0.9
- **Pass/Fail Criteria:** RAG pipeline must NOT be invoked

### TS-002: RAG Pipeline Happy Path
- **Requirement:** FR-012, FR-013, FR-015
- **Type:** Unit (with mocked services)
- **Preconditions:** Mock search returns chunks, mock OpenAI returns answer
- **Steps:**
  1. Create RAGPipeline with mocked dependencies
  2. Call `process_query("conv-1", "What is the PTO policy?")`
  3. Assert response contains content, citations, and disclaimer
- **Expected Result:** Answer grounded in context, citations present, disclaimer included
- **Pass/Fail Criteria:** response_type == "answer", len(citations) > 0, disclaimer present

### TS-003: LLM Fallback Mode
- **Requirement:** NFR-006
- **Type:** Unit (with mocked services)
- **Preconditions:** Mock OpenAI `is_available()` returns False
- **Steps:**
  1. Create RAGPipeline where OpenAI is unavailable
  2. Call `process_query("conv-1", "What is the PTO policy?")`
  3. Assert response is keyword fallback
- **Expected Result:** response_type == "fallback_search", fallback_notice present
- **Pass/Fail Criteria:** No LLM call made, keyword search results returned

### TS-004: Admin Authorization Boundary
- **Requirement:** NFR-010
- **Type:** Integration
- **Preconditions:** Two users — one Employee, one Administrator
- **Steps:**
  1. Call GET /v1/admin/documents with Employee token → 403
  2. Call GET /v1/admin/documents with Administrator token → 200
- **Expected Result:** RBAC enforced correctly
- **Pass/Fail Criteria:** Employee gets 403, Administrator gets 200

### TS-005: Health Endpoint
- **Requirement:** Enterprise security policy
- **Type:** Integration
- **Preconditions:** Service is running
- **Steps:**
  1. Call GET /health without auth → 200
  2. Assert response contains {"status": "healthy"}
- **Expected Result:** No auth required, returns healthy status
- **Pass/Fail Criteria:** Status code 200, body matches spec
