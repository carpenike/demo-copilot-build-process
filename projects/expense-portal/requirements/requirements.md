# Requirements: Employee Expense Management Portal

> **Version:** 1.0
> **Status:** Draft
> **Date:** 2026-03-13
> **Produced by:** Requirements Agent
> **Input source:** `projects/expense-portal/input/business-requirements.md`

---

## 1. Project Summary

Acme Corporation needs to replace its paper-based, email-driven expense reimbursement process with a web-based Employee Expense Management Portal. The system will allow employees to submit expenses digitally (with receipt image capture and OCR), managers to approve or reject them through a configurable workflow, and Finance to close and reconcile against budget in near real time. The portal integrates with Workday for org hierarchy data and SAP S/4HANA for GL coding and payment processing. The primary business goal is to reduce the expense reimbursement cycle from 12–15 business days to 3 business days while enforcing policy compliance at 95%+.

---

## 2. Stakeholders

| Role | Name / Team | Interest |
|------|-------------|----------|
| Executive Sponsor | VP Finance | Budget approval, compliance, final sign-off |
| Product Owner | Finance Systems Team | System accuracy, ERP integration, requirements, UAT |
| Technical Owner | Platform Engineering | Architecture, security, enterprise standards compliance |
| Integration Partner | HR / Workday Admin | Employee data accuracy, integration design |
| End Users | All Employees (~2,400) | Fast, easy expense reimbursement |
| Approvers | Cost Center Managers | Budget visibility, approval control, UAT |
| Reviewer | IT Security | Data protection, access control, security review |

---

## 3. Functional Requirements

### 3.1 Expense Submission

**FR-001:** The system SHALL allow authenticated employees to create a new expense report with a title, date range, business purpose, and one or more line items.

**FR-002:** Each line item SHALL capture: date, category, vendor name, amount, currency (USD or CAD), description, and an optional receipt attachment.

**FR-003:** The system SHALL accept receipt images in JPEG, PNG, and PDF format, up to 10 MB per file.

**FR-004:** The system SHALL apply OCR to uploaded receipts and pre-populate amount, vendor, and date fields where extraction confidence exceeds 85%.

**FR-005:** The system SHALL validate each line item against the current expense policy before allowing submission and SHALL display specific policy violations inline.

**FR-006:** The system SHALL allow employees to save a draft expense report and return to it before submission.

**FR-007:** The system SHALL detect duplicate submissions (same employee, same date, same amount, same vendor) and warn the user before allowing submission.

### 3.2 Approval Workflow

**FR-008:** Upon submission, the system SHALL route the expense report to the submitting employee's direct manager (as defined in Workday) for first-level approval.

**FR-009:** The system SHALL escalate expense reports with any single line item exceeding $500 to Finance for secondary review after manager approval.

**FR-010:** Approvers SHALL be able to approve, reject, or request more information on a report from both the web interface and email notification action links.

**FR-011:** The system SHALL automatically escalate reports with no action taken within 5 business days to the approver's manager.

**FR-012:** When an expense report is rejected, the employee SHALL receive a notification with the rejection reason and a link to edit and resubmit.

### 3.3 Policy Engine

**FR-013:** Finance administrators SHALL be able to configure per-category daily limits, which the policy engine enforces at submission time.

**FR-014:** The system SHALL flag any line item where the claimed amount exceeds the per diem rate for the selected category and destination.

**FR-015:** The system SHALL enforce a configurable list of non-reimbursable expense categories (e.g., personal entertainment, alcohol above policy limit).

### 3.4 Integrations

**FR-016:** The system SHALL synchronize employee, manager hierarchy, and cost center data from Workday on a nightly scheduled basis.

**FR-017:** Upon Finance approval, the system SHALL generate a payment batch file in SAP IDoc format and transmit it to the SAP S/4HANA interface.

**FR-018:** The system SHALL write a GL journal entry record to SAP upon final approval, coded to the appropriate cost center and GL account.

### 3.5 Notifications

**FR-019:** The system SHALL send email and in-app notifications for the following events: expense report submitted, approved, rejected, returned for more information, and escalated.

**FR-020:** Notification content SHALL include the report title, total amount, and a direct link to the relevant report.

### 3.6 Reporting & Dashboards

**FR-021:** Finance SHALL have access to a reporting dashboard showing: total expenses by period, by cost center, by category, and by approval status.

**FR-022:** Managers SHALL see a dashboard showing their team's submitted and approved expenses vs. cost center budget for the current period.

**FR-023:** All reports SHALL be exportable to CSV.

### 3.7 Administration

**FR-024:** Finance administrators SHALL be able to configure expense policy rules, category management, and approval threshold settings via an admin panel.

---

## 4. Non-Functional Requirements

### 4.1 Performance

**NFR-001:** The portal SHALL respond to 95% of page load requests within 2 seconds under normal load (up to 500 concurrent users).

**NFR-002:** OCR processing of receipt images SHALL complete within 10 seconds for files under 5 MB.

**NFR-003:** SAP IDoc batch generation SHALL complete within 60 seconds for batches up to 1,000 line items.

### 4.2 Availability

**NFR-004:** The portal SHALL maintain 99.5% uptime during business hours (7:00 AM – 7:00 PM local time, Monday–Friday).

**NFR-005:** Planned maintenance windows SHALL be outside business hours with 48 hours' advance notice.

**NFR-006:** The system SHALL preserve in-progress expense drafts in the event of an unexpected outage.

### 4.3 Security

**NFR-007:** All access SHALL require SSO authentication via the corporate Okta identity provider.

**NFR-008:** Role-based access control SHALL enforce that employees can only view their own reports; managers can only view direct reports' submissions.

**NFR-009:** Receipt images and financial data SHALL be encrypted at rest using AES-256.

**NFR-010:** All data transmission SHALL use TLS 1.2 or higher.

**NFR-011:** The system SHALL log all approval actions with actor, timestamp, and IP address for audit purposes, retained for 7 years.

### 4.4 Scalability

**NFR-012:** The system SHALL scale horizontally to handle a 3x increase in submission volume (target peak: 1,500 concurrent users) without architectural changes.

### 4.5 Compliance

**NFR-013:** Receipt storage SHALL comply with IRS recordkeeping requirements (7-year retention minimum).

**NFR-014:** The system SHALL support SOX audit requirements: immutable approval logs, no post-approval editing of expense data, and segregation of duties between submitter and approver.

---

## 5. Out of Scope

- Corporate credit card reconciliation (separate initiative, Q4 2026)
- Travel booking (existing travel portal continues to serve this need)
- Native iOS or Android applications (mobile-responsive web is sufficient for v1)
- Multi-currency support beyond USD and CAD (future release)
- Integration with payroll for same-day reimbursement (EFT via SAP covers this)
- Delegate submission (EA submitting on behalf of executive) — pending open question resolution

---

## 6. Assumptions

1. All employees have corporate Okta SSO credentials and can authenticate via existing identity infrastructure.
2. Workday contains accurate, current manager hierarchy data. The portal will not maintain its own org chart.
3. The SAP S/4HANA integration team will provide IDoc schema documentation and a sandbox environment by Week 3 of the project.
4. Finance will provide finalized expense policy rules (per diem limits, category definitions) at least 4 weeks before UAT.
5. Approximately 2,400 employees are in scope for v1.
6. Mobile-responsive web (not native apps) is acceptable for mobile use cases.
7. Nightly Workday sync is sufficient for org hierarchy updates (pending open question #4).

---

## 7. Open Questions

| # | Question | Owner | Due Date | Resolution |
|---|----------|-------|----------|------------|
| 1 | Does the system need to support expense reports submitted on behalf of another employee (e.g., EA submitting for executive)? | Finance Systems | Mar 27, 2026 | Open |
| 2 | What is the maximum number of line items per expense report? | Finance Systems | Mar 27, 2026 | Open |
| 3 | Should managers be able to partially approve a report (approve some line items, reject others)? | VP Finance | Apr 3, 2026 | Open |
| 4 | Is real-time Workday sync required for manager reassignment, or is nightly sufficient? | Workday Admin | Apr 3, 2026 | Open |
| 5 | Will Canada-based employees require French language support for v1? | HR | Apr 10, 2026 | Open |

---

## 8. Governance Flags

| Flag | Requirement | Conflict | Resolution |
|------|-------------|----------|------------|
| GF-001 | FR-010 — Email notification action links | Enterprise security policy requires all endpoints behind API gateway; email deep-links with embedded approval tokens must be reviewed by IT Security to ensure no unauthenticated state changes occur. | Route to IT Security review during design phase. Token-based actions must still require SSO session validation. |
| GF-002 | NFR-007 — Okta SSO | Enterprise standards mandate SSO but do not specify Okta explicitly. Confirm Okta is the approved corporate IdP with Platform Engineering. | Verify with Platform Engineering; no block expected. |
| GF-003 | FR-004 — OCR processing | OCR may require a third-party service or ML model. If a SaaS OCR API is used, it must be evaluated against the enterprise security policy (no data leaving approved cloud boundaries). | Evaluate during design: self-hosted (e.g., Tesseract) vs. approved SaaS. Data residency must be maintained. |

*All technology and language choices deferred to the Design Agent. No language policy conflicts detected — the input document already acknowledges the Python/Go constraint.*
