# Requirements: Support Ticket Portal

> **Version:** 1.0
> **Status:** Approved
> **Date:** 2026-03-13
> **Produced by:** Requirements Agent
> **Input source:** `projects/example-ticket-app/input/request.md`

---

## 1. Project Summary

The Support Ticket Portal is a web-based system that enables external customers
to submit and track support requests, and internal support agents to manage,
assign, and resolve those tickets. The system replaces ad-hoc email-based support
with a structured, searchable, and auditable workflow. A reporting dashboard
provides leadership with visibility into ticket volume, resolution time, and
agent performance.

---

## 2. Stakeholders

| Role | Name / Team | Interest |
|------|-------------|----------|
| Product Owner | Support Operations | Workflow efficiency, customer satisfaction |
| Engineering Lead | Platform Engineering | Architecture, standards compliance |
| End Users (External) | Customers | Fast, transparent issue resolution |
| End Users (Internal) | Support Agents | Efficient ticket management |
| Executive Sponsor | CEO | KPI dashboard, operational visibility |

---

## 3. Functional Requirements

### 3.1 Customer Ticket Submission

**FR-001:** The system SHALL allow authenticated customers to submit a support
ticket with a subject, description, and priority level (Low, Medium, High).

**FR-002:** The system SHALL allow customers to attach files (images, PDFs, logs)
up to 10MB per file, maximum 5 attachments per ticket.

**FR-003:** The system SHALL assign a unique ticket ID to each submission and
display a confirmation with the ticket ID to the customer.

**FR-004:** The system SHALL allow customers to view a list of their own tickets,
filtered by status and date range.

**FR-005:** The system SHALL allow customers to add comments to their open tickets.

### 3.2 Support Agent Workflow

**FR-006:** The system SHALL provide support agents with a queue view showing all
unassigned and assigned-to-me tickets, sortable by priority, date, and status.

**FR-007:** The system SHALL allow agents to assign tickets to themselves or to
other agents.

**FR-008:** The system SHALL allow agents to update ticket status through defined
states: Open → In Progress → Waiting on Customer → Resolved → Closed.

**FR-009:** The system SHALL allow agents to add internal notes to a ticket that
are NOT visible to the customer.

**FR-010:** The system SHALL support full-text search across ticket subject,
description, and comments.

**FR-011:** The system SHALL allow agents to export a filtered ticket list to CSV.

### 3.3 Notifications

**FR-012:** The system SHALL send an email notification to the customer when their
ticket status changes, including the new status and any agent-visible comments.

**FR-013:** The system SHALL send an email notification to the assigned agent when
a customer adds a comment to their ticket.

### 3.4 Reporting Dashboard

**FR-014:** The system SHALL provide a dashboard showing: total ticket volume by
period, average resolution time, tickets by status, and tickets by priority.

**FR-015:** The system SHALL provide per-agent performance metrics: tickets
resolved, average resolution time, and current open ticket count.

**FR-016:** Dashboard data SHALL refresh at most every 5 minutes (not real-time).

---

## 4. Non-Functional Requirements

### 4.1 Performance
**NFR-001:** The API SHALL respond to 95% of requests within 200ms at 100
requests/second sustained load.
**NFR-002:** Full-text search results SHALL return within 500ms for indices up to
1 million tickets.

### 4.2 Availability
**NFR-003:** The service SHALL maintain 99.9% uptime measured monthly (< 43.2
minutes downtime/month).

### 4.3 Security
**NFR-004:** All API endpoints SHALL require authentication via JWT bearer tokens.
**NFR-005:** Customers SHALL only be able to view and modify their own tickets.
Agents SHALL be able to view and modify all tickets.
**NFR-006:** All data in transit SHALL use TLS 1.2+.
**NFR-007:** All data at rest SHALL be encrypted using AES-256.

### 4.4 Scalability
**NFR-008:** The system SHALL handle up to 5,000 tickets per day without
architectural changes.

### 4.5 Compliance
**NFR-009:** No customer PII SHALL be logged in application logs.

---

## 5. Out of Scope

- Real-time chat or live support
- SLA enforcement / automatic escalation (future release)
- Multi-language / i18n support
- Native mobile applications
- Customer self-service knowledge base

---

## 6. Assumptions

- Customers authenticate via an existing OAuth2 identity provider
- The existing PostgreSQL database is available and will be used for persistence
- SendGrid is the approved email provider and an API key is available via Secrets Manager
- Support agents are managed as a user role and provisioned by admin

---

## 7. Open Questions

| # | Question | Owner | Due Date | Resolution |
|---|----------|-------|----------|------------|
| 1 | Maximum concurrent agents expected? | Support Ops | Mar 20 | ~50 agents |
| 2 | Ticket data retention policy? | Legal | Mar 27 | Open |
| 3 | SLA tiers for different customer plans? | Product | Deferred | Out of scope for v1 |

---

## 8. Governance Flags

| Flag | Requirement | Conflict | Resolution |
|------|-------------|----------|------------|
| LANG-001 | Stakeholder requested Node.js backend | **BLOCKED** by language policy — only Python and Go are approved | Use Python (FastAPI) as the approved alternative |
| LANG-002 | Stakeholder suggested React dashboard | **BLOCKED** by language policy — frontend frameworks not in approved list | Serve dashboard via server-rendered templates or API-only backend with approved tooling |

*Two governance conflicts identified. Both resolved by selecting approved alternatives.*
