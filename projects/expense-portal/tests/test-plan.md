# Test Plan: Employee Expense Management Portal

> **Version:** 1.0
> **Status:** Draft
> **Date:** 2026-03-13
> **Produced by:** Test Agent
> **Input sources:**
> - `projects/expense-portal/requirements/requirements.md`
> - `projects/expense-portal/requirements/user-stories.md`
> - `projects/expense-portal/design/wireframe-spec.md`

---

## 1. Scope

### In Scope
- Core business logic: policy engine, approval workflow state machine, duplicate detection
- All REST API endpoints (25+ endpoints across 7 routers)
- Authentication and authorization (OIDC flow, RBAC, email action tokens)
- Database model integrity and constraint enforcement
- Error handling (RFC 7807 Problem Details, validation errors)
- CSV export for finance and manager dashboards
- Receipt upload validation (file type, file size)
- Operational endpoints (/health, /ready, /metrics)

### Out of Scope
- Frontend/UI testing (Jinja2 templates — deferred to E2E when templates are built)
- External service live integration (Workday, SAP, Azure Document Intelligence — tested via mocks)
- Load/performance testing (deferred to `tests/load/` — infrastructure must be provisioned first)
- Azure Blob Storage live integration (mocked in tests)

---

## 2. Test Strategy

| Test Type | Scope | Framework | Coverage Target |
|-----------|-------|-----------|-----------------|
| Unit | Core business logic (policy_engine, approval_workflow, duplicate_detector) | pytest + pytest-asyncio | 80% line coverage on core/ |
| Integration | API endpoints + database (mocked) | pytest + httpx AsyncClient | All endpoints, all status codes |
| Security | Auth/authz edge cases | pytest | All 401/403 scenarios |
| Contract | OpenAPI spec conformance | Manual verification (openapi.yaml committed) | 100% of endpoints documented |

---

## 3. Requirements Coverage Matrix

| Requirement | Test Type | Test ID | Description | Status |
|-------------|-----------|---------|-------------|--------|
| FR-001 | Integration | IT-EXP-001 | Create expense report with required fields | Planned |
| FR-001 | Integration | IT-EXP-002 | Reject creation with missing required fields | Planned |
| FR-002 | Integration | IT-EXP-003 | Add line item with all fields | Planned |
| FR-002 | Integration | IT-EXP-004 | Reject line item with invalid currency | Planned |
| FR-003 | Integration | IT-REC-001 | Upload JPEG receipt under 10 MB | Planned |
| FR-003 | Integration | IT-REC-002 | Reject file over 10 MB | Planned |
| FR-003 | Integration | IT-REC-003 | Reject unsupported file type | Planned |
| FR-004 | Unit | UT-OCR-001 | OCR confidence filtering at 85% threshold | Planned |
| FR-005 | Unit | UT-POL-001 | Policy validation — happy path (no violations) | Planned |
| FR-005 | Unit | UT-POL-002 | Policy validation — daily limit exceeded | Planned |
| FR-005 | Unit | UT-POL-003 | Policy validation — non-reimbursable category | Planned |
| FR-005 | Unit | UT-POL-004 | Policy validation — per diem exceeded | Planned |
| FR-005 | Integration | IT-EXP-005 | Submit report — blocked by policy violations | Planned |
| FR-006 | Integration | IT-EXP-006 | Save draft and retrieve later | Planned |
| FR-007 | Unit | UT-DUP-001 | Duplicate detection — match found | Planned |
| FR-007 | Unit | UT-DUP-002 | Duplicate detection — no match | Planned |
| FR-007 | Integration | IT-EXP-007 | Submit with duplicate warning, acknowledge and proceed | Planned |
| FR-008 | Unit | UT-WF-001 | Route to manager on submission | Planned |
| FR-008 | Integration | IT-APR-001 | Manager receives report in pending queue | Planned |
| FR-009 | Unit | UT-WF-002 | Finance escalation for line items > $500 | Planned |
| FR-009 | Unit | UT-WF-003 | No finance escalation when all items <= $500 | Planned |
| FR-010 | Integration | IT-APR-002 | Approve via API | Planned |
| FR-010 | Integration | IT-APR-003 | Reject via API | Planned |
| FR-010 | Integration | IT-APR-004 | Request more info via API | Planned |
| FR-010 | Integration | IT-APR-005 | Email action token — approve | Planned |
| FR-011 | Unit | UT-WF-004 | Escalation to approver's manager | Planned |
| FR-012 | Integration | IT-APR-006 | Rejected report editable and resubmittable | Planned |
| FR-013 | Unit | UT-POL-005 | Configurable per-category daily limits | Planned |
| FR-014 | Unit | UT-POL-006 | Per diem rate enforcement | Planned |
| FR-015 | Unit | UT-POL-007 | Non-reimbursable category blocking | Planned |
| FR-016 | Unit | UT-SYNC-001 | Workday sync task upserts employees | Planned |
| FR-017 | Unit | UT-SAP-001 | IDoc batch generation | Planned |
| FR-018 | Unit | UT-SAP-002 | GL journal entry creation | Planned |
| FR-019 | Integration | IT-RPT-001 | Finance dashboard — returns summary data | Planned |
| FR-019 | Integration | IT-RPT-002 | Finance dashboard — filter by cost center | Planned |
| FR-020 | Integration | IT-RPT-003 | Manager dashboard — team spend vs budget | Planned |
| FR-021 | Integration | IT-RPT-004 | CSV export — finance report | Planned |
| FR-021 | Integration | IT-RPT-005 | CSV export — manager report | Planned |
| FR-022 | Unit | UT-NOTIF-001 | Submission notification sent to approver | Planned |
| FR-023 | Unit | UT-NOTIF-002 | Approval reminder for pending reports | Planned |
| FR-024 | Integration | IT-ADM-001 | Create expense category | Planned |
| FR-024 | Integration | IT-ADM-002 | Update category daily limit | Planned |
| FR-024 | Integration | IT-ADM-003 | Update approval thresholds | Planned |
| NFR-007 | Security | SEC-001 | Unauthenticated request → 401 | Planned |
| NFR-008 | Security | SEC-002 | Employee cannot view other's report → 403 | Planned |
| NFR-008 | Security | SEC-003 | Manager can only view direct reports' data | Planned |
| NFR-015 | Security | SEC-004 | Submitter cannot approve own report | Planned |
| NFR-015 | Security | SEC-005 | Approval actions are immutable (audit trail) | Planned |
| NFR-019 | Integration | IT-OPS-001 | /health returns 200 | Planned |
| NFR-019 | Integration | IT-OPS-002 | /ready returns 200 when DB healthy | Planned |
| NFR-022 | Integration | IT-EXP-008 | Cursor-based pagination on list endpoint | Planned |
| NFR-023 | Integration | IT-EXP-009 | Error responses follow RFC 7807 format | Planned |

---

## 4. Test Scenarios

### TS-001: Employee submits a valid expense report

- **Requirement:** FR-001, FR-002, FR-008
- **Type:** Integration
- **Preconditions:** Authenticated employee with a manager assigned
- **Steps:**
  1. POST /v1/expenses/reports — create report
  2. POST /v1/expenses/reports/{id}/line-items — add line item
  3. POST /v1/expenses/reports/{id}/submit — submit
- **Expected Result:** Report status → "submitted", routed_to contains manager info
- **Pass/Fail Criteria:** 200 OK with correct status and approver

### TS-002: Policy engine blocks non-reimbursable category

- **Requirement:** FR-005, FR-015
- **Type:** Unit
- **Preconditions:** Category marked as non-reimbursable
- **Steps:**
  1. Create line item in non-reimbursable category
  2. Run validate_line_items()
- **Expected Result:** Returns blocking violation with rule="non_reimbursable"
- **Pass/Fail Criteria:** Violation is_blocking=True, correct message

### TS-003: Manager approval triggers finance review for high-value items

- **Requirement:** FR-009
- **Type:** Unit
- **Preconditions:** Report with line item > $500, threshold set at $500
- **Steps:**
  1. Call approve_report() on a submitted report
- **Expected Result:** Status changes to "finance_review"
- **Pass/Fail Criteria:** Returns ("finance_review", "finance_review")

### TS-004: Duplicate detection warns on matching submission

- **Requirement:** FR-007
- **Type:** Unit
- **Preconditions:** Prior submitted report with matching line item (same date, amount, vendor)
- **Steps:**
  1. Call check_duplicates() with matching line item
- **Expected Result:** Returns DuplicateWarning with matching report number
- **Pass/Fail Criteria:** Warning message contains the matched report number

### TS-005: Email action token — single-use enforcement

- **Requirement:** FR-010, NFR-015
- **Type:** Integration
- **Preconditions:** Valid action token created for approver
- **Steps:**
  1. GET /v1/approvals/actions/{token} — first use
  2. GET /v1/approvals/actions/{token} — second use
- **Expected Result:** First call succeeds; second call returns 400 "already used"
- **Pass/Fail Criteria:** Token is_used=True after first call

---

## 5. Auth & Security Test Cases

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| SEC-001 | Unauthenticated request to GET /v1/expenses/reports | 401 Unauthorized |
| SEC-002 | Employee views another employee's report | 403 Forbidden |
| SEC-003 | Manager views non-direct-report's report | 403 Forbidden |
| SEC-004 | Employee attempts to access admin panel | 403 Forbidden |
| SEC-005 | Non-approver attempts to approve a report | 403 Forbidden |
| SEC-006 | Submitter attempts to approve own report | Routed to manager's manager (segregation of duties) |
| SEC-007 | Expired email action token | 400 Bad Request |
| SEC-008 | Used email action token (replay attempt) | 400 Bad Request |
| SEC-009 | Email action token with wrong user | 403 Forbidden |
| SEC-010 | PATCH on approved report (immutability) | 409 Conflict |
| SEC-011 | Non-finance user accesses finance dashboard | 403 Forbidden |

---

## 6. Error Path Test Cases

| Test ID | Scenario | Expected Behavior |
|---------|----------|-------------------|
| ERR-001 | POST report with end_date < start_date | 400 with validation message |
| ERR-002 | POST line item with invalid category | 400 "Invalid category" |
| ERR-003 | POST line item with invalid currency (EUR) | 400 validation error |
| ERR-004 | Submit report with no line items | 400 "Report has no line items" |
| ERR-005 | Upload receipt > 10 MB | 400 "File exceeds 10 MB limit" |
| ERR-006 | Upload .exe file as receipt | 400 "Unsupported file format" |
| ERR-007 | GET report that doesn't exist | 404 "Report not found" |
| ERR-008 | PATCH report in "submitted" status | 409 "Report is not editable" |
| ERR-009 | Approve report in "draft" status | 403/409 error |
| ERR-010 | Create duplicate category name | 409 "Category already exists" |

---

## 7. Test Environment

| Component | Details |
|-----------|---------|
| Runtime | Python 3.11+ |
| Test framework | pytest + pytest-asyncio |
| HTTP client | httpx AsyncClient (FastAPI TestClient) |
| Database | SQLAlchemy async session (mocked via fixtures) |
| External services | All mocked (Blob Storage, Document Intelligence, SMTP, Workday, SAP) |
| CI Integration | Tests run in `test` stage of GitHub Actions CI pipeline |

---

## 8. Exit Criteria

- [ ] Every FR (FR-001 through FR-024) has at least one test
- [ ] Every user story acceptance criterion has a corresponding test
- [ ] All API endpoints have integration tests for success and error cases
- [ ] Auth/authz edge cases covered (401, 403 for all protected endpoints)
- [ ] Error paths tested (validation, not-found, conflict, policy violations)
- [ ] Tests are independent (no test depends on another test's state)
- [ ] 80% line coverage on core/ modules
