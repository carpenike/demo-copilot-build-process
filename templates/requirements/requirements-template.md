# Requirements: [Project Name]

> **Version:** 1.0
> **Status:** [Draft | In Review | Approved]
> **Date:** YYYY-MM-DD
> **Produced by:** Requirements Agent
> **Input source:** `projects/<project>/input/request.md`

---

## 1. Project Summary

One paragraph describing what this project is, why it exists, and who it serves.

---

## 2. Stakeholders

| Role | Name / Team | Interest |
|------|-------------|----------|
| Product Owner | | Final requirements approval |
| Engineering Lead | | Technical feasibility |
| End Users | | Using the system |

---

## 3. Functional Requirements

> Format: `FR-XXX: The system SHALL/SHOULD/MAY [verb] [object] [condition]`

### 3.1 [Feature Area 1]

**FR-001:** The system SHALL ...
**FR-002:** The system SHALL ...
**FR-003:** The system SHOULD ...

### 3.2 [Feature Area 2]

**FR-004:** The system SHALL ...

---

## 4. Non-Functional Requirements

### 4.1 Performance
**NFR-001:** The API SHALL respond to 95% of requests within [X]ms at [Y] requests/second sustained load.
**NFR-002:** The system SHALL support up to [N] concurrent users.

### 4.2 Availability
**NFR-003:** The service SHALL maintain 99.9% uptime measured monthly (< 43.2 minutes downtime/month).

### 4.3 Security
**NFR-004:** All API endpoints SHALL require authentication via [mechanism].
**NFR-005:** Data at rest SHALL be encrypted using AES-256.
**NFR-006:** All service-to-service communication SHALL use TLS 1.2 or higher.

### 4.4 Scalability
**NFR-007:** The system SHALL scale horizontally to handle [N]x baseline load without code changes.

### 4.5 Compliance
**NFR-008:** [Any regulatory or data handling requirements]

---

## 5. Out of Scope

Explicitly list what this project does NOT include. This is as important as what it does.

- [Out of scope item 1]
- [Out of scope item 2]

---

## 6. Assumptions

List assumptions made during requirements gathering that, if wrong, would change the requirements.

- [Assumption 1]
- [Assumption 2]

---

## 7. Open Questions

| # | Question | Owner | Due Date | Resolution |
|---|----------|-------|----------|------------|
| 1 | | | | |

---

## 8. Governance Flags

> Any conflicts between stakeholder requests and enterprise standards.

| Flag | Requirement | Conflict | Resolution |
|------|-------------|----------|------------|
| | | | |

*No flags = all requirements are within enterprise standards.*
