# Test Plan: [Project Name]

> **Version:** 1.0
> **Status:** [Draft | In Review | Approved]
> **Date:** YYYY-MM-DD
> **Produced by:** Test Agent
> **Input sources:**
> - `projects/<project>/requirements/requirements.md`
> - `projects/<project>/requirements/user-stories.md`
> - `projects/<project>/design/wireframe-spec.md`

---

## 1. Scope

### In Scope
[What is being tested — list the functional areas, APIs, and flows]

### Out of Scope
[What is NOT being tested in this plan and why]

---

## 2. Test Strategy

| Test Type | Scope | Framework | Coverage Target |
|-----------|-------|-----------|-----------------|
| Unit | Core business logic | pytest / testing+testify | 80% line coverage |
| Integration | API + database | pytest + testcontainers | All endpoints |
| Contract | OpenAPI spec conformance | schemathesis | 100% of endpoints |
| E2E | Critical user flows | playwright / k6 | Happy paths + key errors |
| Load | NFR latency/throughput targets | locust / k6 | All NFR performance targets |

---

## 3. Requirements Coverage Matrix

| Requirement | Test Type | Test ID | Description | Status |
|-------------|-----------|---------|-------------|--------|
| FR-001 | Unit | UT-001 | [Description] | Planned |
| FR-001 | Integration | IT-001 | [Description] | Planned |
| FR-002 | Unit | UT-002 | [Description] | Planned |
| NFR-001 | Load | LT-001 | [Description] | Planned |

---

## 4. Test Scenarios

### TS-001: [Scenario Name]

- **Requirement:** FR-001
- **Type:** Unit
- **Preconditions:** [Setup needed]
- **Steps:**
  1. [Step 1]
  2. [Step 2]
- **Expected Result:** [What should happen]
- **Pass/Fail Criteria:** [How to determine pass or fail]

---

### TS-002: [Scenario Name]

[Repeat structure above]

---

## 5. Auth & Security Test Cases

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| SEC-001 | Unauthenticated request to protected endpoint | 401 Unauthorized |
| SEC-002 | Authenticated user accessing another user's resource | 403 Forbidden |
| SEC-003 | Expired token | 401 Unauthorized |
| SEC-004 | SQL injection in query parameters | 400 Bad Request (no data leak) |
| SEC-005 | XSS payload in text fields | Sanitized output |

---

## 6. Error Path Test Cases

| Test ID | Scenario | Expected Behavior |
|---------|----------|-------------------|
| ERR-001 | Database unavailable | `/ready` returns 503; requests return appropriate error |
| ERR-002 | Malformed request body | 400 with RFC 7807 error detail |
| ERR-003 | Rate limit exceeded | 429 Too Many Requests |

---

## 7. Test Environment

| Component | Details |
|-----------|---------|
| Runtime | [Python 3.11+ / Go 1.22+] |
| Database | [PostgreSQL via testcontainers] |
| CI Integration | Tests run in `test` stage of CI pipeline |

---

## 8. Exit Criteria

- [ ] All FR requirements have at least one passing test
- [ ] All user story acceptance criteria have corresponding tests
- [ ] Unit test coverage ≥ 80% on core logic
- [ ] All integration tests pass against a clean database
- [ ] Zero critical or high severity bugs open
- [ ] Auth boundary tests all pass
