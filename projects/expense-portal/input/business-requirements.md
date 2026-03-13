# Business Requirements Document
## Employee Expense Management Portal

| | |
|---|---|
| **Document Version** | 1.0 — Draft |
| **Date** | March 13, 2026 |
| **Prepared By** | Finance Systems Team |
| **Status** | Pending Engineering Review |
| **Project Code** | FIN-EXP-2026 |

*CONFIDENTIAL — INTERNAL USE ONLY*

---

## 1. Executive Summary

Acme Corporation currently manages employee expense reimbursements through a combination of paper forms, email approvals, and manual entry into the ERP system. This process is slow, error-prone, and produces no real-time visibility into spend. Finance closes expenses 12–15 business days after a reporting period ends.

This document defines the requirements for an Employee Expense Management Portal — a web-based system that enables employees to submit expenses digitally, managers to approve or reject them, and Finance to close and reconcile against budget in near real time.

The system will integrate with the existing HR system (Workday) for employee and manager hierarchy data, and with the ERP (SAP S/4HANA) for GL coding and payment processing.

---

## 2. Business Objectives

This project is being initiated to address the following measurable business outcomes:

- Reduce average expense reimbursement cycle time from 12–15 business days to 3 business days
- Eliminate 100% of paper-based expense forms within 6 months of go-live
- Reduce Finance manual data entry effort by 80% through ERP integration
- Provide real-time budget vs. actuals visibility to cost center managers
- Achieve policy compliance rate of 95%+ through automated policy enforcement
- Support mobile receipt capture to eliminate lost receipts

---

## 3. Project Scope

### 3.1 In Scope

- Employee expense submission (web and mobile-responsive)
- Receipt capture and storage (image upload, OCR extraction)
- Multi-level approval workflow (manager approval, Finance review for amounts over $500)
- Automated policy enforcement (per diem limits, category restrictions, duplicate detection)
- Integration with Workday for employee, manager, and cost center data
- Integration with SAP S/4HANA for GL coding and payment batch generation
- Email and in-app notifications for submission, approval, and rejection events
- Reporting dashboard for Finance: expense totals by cost center, category, and period
- Manager dashboard: pending approvals, team spend vs. budget
- Admin panel: policy configuration, category management, approval threshold settings

### 3.2 Out of Scope

- Corporate credit card reconciliation (separate initiative, Q4 2026)
- Travel booking (employees will continue using the existing travel portal)
- Native iOS or Android applications (mobile-responsive web is sufficient for v1)
- Multi-currency support beyond USD and CAD (future release)
- Integration with payroll for same-day reimbursement (EFT via SAP covers this)

---

## 4. Stakeholders

| Name / Team | Role | Interest | Involvement |
|---|---|---|---|
| VP Finance | Executive Sponsor | Budget approval, compliance | Final sign-off |
| Finance Systems Team | Product Owner | System accuracy, ERP integration | Requirements, UAT |
| Platform Engineering | Technical Owner | Architecture, security, standards | Design, build, deploy |
| HR / Workday Admin | Integration Partner | Employee data accuracy | Integration design |
| All Employees | End Users | Fast, easy reimbursement | UAT, training |
| Cost Center Managers | Approvers | Budget visibility, control | UAT, training |
| IT Security | Reviewer | Data protection, access control | Security review |

---

## 5. Functional Requirements

### 5.1 Expense Submission

- **FR-001:** The system SHALL allow authenticated employees to create a new expense report with a title, date range, business purpose, and one or more line items.
- **FR-002:** Each line item SHALL capture: date, category, vendor name, amount, currency (USD/CAD), description, and an optional receipt attachment.
- **FR-003:** The system SHALL accept receipt images in JPEG, PNG, and PDF format up to 10MB per file.
- **FR-004:** The system SHALL apply OCR to uploaded receipts and pre-populate amount, vendor, and date fields where extraction confidence exceeds 85%.
- **FR-005:** The system SHALL validate each line item against the current expense policy before allowing submission, and display specific policy violations inline.
- **FR-006:** The system SHALL allow employees to save a draft expense report and return to it before submission.
- **FR-007:** The system SHALL detect duplicate submissions (same employee, same date, same amount, same vendor) and warn before allowing submission.

### 5.2 Approval Workflow

- **FR-008:** Upon submission, the system SHALL route the expense report to the submitting employee's direct manager in Workday for first-level approval.
- **FR-009:** The system SHALL escalate expense reports with any single line item exceeding $500 to Finance for secondary review after manager approval.
- **FR-010:** Approvers SHALL be able to approve, reject, or request more information on a report from both the web interface and email notification links.
- **FR-011:** The system SHALL automatically escalate reports with no action taken within 5 business days to the approver's manager.
- **FR-012:** When an expense report is rejected, the employee SHALL receive a notification with the rejection reason and a link to edit and resubmit.

### 5.3 Policy Engine

- **FR-013:** Finance administrators SHALL be able to configure per-category daily limits, which the policy engine enforces at submission time.
- **FR-014:** The system SHALL flag any line item where the claimed amount exceeds the per diem rate for the selected category and destination.
- **FR-015:** The system SHALL enforce a configurable list of non-reimbursable expense categories (e.g., personal entertainment, alcohol above policy limit).

### 5.4 Integrations

- **FR-016:** The system SHALL synchronize employee, manager hierarchy, and cost center data from Workday on a nightly scheduled basis.
- **FR-017:** Upon Finance approval, the system SHALL generate a payment batch file in SAP IDoc format and transmit it to the SAP S/4HANA interface.
- **FR-018:** The system SHALL write a GL journal entry record to SAP upon final approval, coded to the appropriate cost center and GL account.

### 5.5 Reporting & Dashboards

- **FR-019:** Finance SHALL have access to a reporting dashboard showing: total expenses by period, by cost center, by category, and by approval status.
- **FR-020:** Managers SHALL see a dashboard showing their team's submitted and approved expenses vs. cost center budget for the current period.
- **FR-021:** All reports SHALL be exportable to CSV.

---

## 6. Non-Functional Requirements

### 6.1 Performance

- **NFR-001:** The portal SHALL respond to 95% of page load requests within 2 seconds under normal load (up to 500 concurrent users).
- **NFR-002:** OCR processing of receipt images SHALL complete within 10 seconds for files under 5MB.
- **NFR-003:** SAP IDoc batch generation SHALL complete within 60 seconds for batches up to 1,000 line items.

### 6.2 Availability & Reliability

- **NFR-004:** The portal SHALL maintain 99.5% uptime during business hours (7am–7pm local time, Monday–Friday).
- **NFR-005:** Planned maintenance windows SHALL be outside business hours with 48 hours' advance notice.
- **NFR-006:** The system SHALL preserve in-progress expense drafts in the event of an unexpected outage.

### 6.3 Security

- **NFR-007:** All access SHALL require SSO authentication via the corporate Microsoft Entra ID identity provider.
- **NFR-008:** Role-based access control SHALL enforce that employees can only view their own reports; managers can only view direct reports' submissions.
- **NFR-009:** Receipt images and financial data SHALL be encrypted at rest using AES-256.
- **NFR-010:** All data transmission SHALL use TLS 1.2 or higher.
- **NFR-011:** The system SHALL log all approval actions with actor, timestamp, and IP address for audit purposes, retained for 7 years.

### 6.4 Scalability

- **NFR-012:** The system SHALL be designed to handle a 3x increase in submission volume without architectural changes (target peak: 1,500 concurrent users).

### 6.5 Compliance

- **NFR-013:** Receipt storage SHALL comply with IRS recordkeeping requirements (7-year retention minimum).
- **NFR-014:** The system SHALL support SOX audit requirements: immutable approval logs, no post-approval editing, segregation of duties between submitter and approver.

---

## 7. Assumptions and Constraints

### 7.1 Assumptions

1. All employees have corporate Microsoft Entra ID SSO credentials and can authenticate via existing identity infrastructure.
2. Workday contains accurate, current manager hierarchy data. The portal will not maintain its own org chart.
3. The SAP S/4HANA integration team will provide IDoc schema documentation and a sandbox environment by Week 3 of the project.
4. Finance will provide finalized expense policy rules (per diem limits, category definitions) at least 4 weeks before UAT.
5. Approximately 2,400 employees are in scope for v1.

### 7.2 Constraints

- Technology choices for this project are governed by the Platform Engineering enterprise standards. **Only Python and Go are approved for new backend services**; any deviation requires an approved Architecture Decision Record (ADR).
- The system must be deployable to the existing Kubernetes (AKS) infrastructure.
- All secrets and credentials must be stored in Azure Key Vault. No credentials may appear in configuration files or source code.
- The project must go live before the Q3 2026 fiscal quarter close (target: **July 1, 2026**).

---

## 8. Open Questions

| # | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| 1 | Does the system need to support expense reports submitted on behalf of another employee (e.g., EA submitting for executive)? | Finance Systems | Mar 27 | Open |
| 2 | What is the maximum number of line items per expense report? | Finance Systems | Mar 27 | Open |
| 3 | Should managers be able to partially approve a report (approve some line items, reject others)? | VP Finance | Apr 3 | Open |
| 4 | Is real-time Workday sync required for the manager reassignment use case, or is nightly sufficient? | Workday Admin | Apr 3 | Open |
| 5 | Will Canada-based employees require French language support for v1? | HR | Apr 10 | Open |

---

## 9. Indicative Timeline

| Milestone | Target Date | Description |
|---|---|---|
| Requirements Approved | March 28, 2026 | Stakeholder sign-off on this document |
| Architecture & ADRs | April 11, 2026 | Technology decisions, ADRs, wireframe spec complete |
| Development Sprint 1 | April 14–April 25 | Auth, employee profile, basic submission form |
| Development Sprint 2 | April 28–May 9 | Approval workflow, notifications, policy engine |
| Development Sprint 3 | May 12–May 23 | SAP & Workday integrations, reporting dashboards |
| UAT | June 2–June 20, 2026 | Finance, manager, and employee user acceptance testing |
| Go-Live | July 1, 2026 | Production launch, Q3 2026 expenses on new system |

---

## 10. Approval & Sign-Off

By signing below, stakeholders confirm they have reviewed this Business Requirements Document and agree it accurately represents the scope and requirements for the Employee Expense Management Portal.

| Name | Role | Signature | Date |
|---|---|---|---|
| | VP Finance (Executive Sponsor) | | |
| | Finance Systems Team Lead | | |
| | Platform Engineering Lead | | |
| | IT Security Lead | | |
