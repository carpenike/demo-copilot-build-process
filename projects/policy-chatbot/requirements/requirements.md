# Requirements: Policy Chatbot

> **Version:** 1.0
> **Status:** Draft
> **Date:** 2026-03-17
> **Produced by:** Requirements Agent
> **Input sources:** `projects/policy-chatbot/input/request.md`, `projects/policy-chatbot/input/business-requirements.md`

---

## 1. Project Summary

Acme Corporation maintains over 140 corporate policy documents spanning HR, IT,
Finance, Facilities, Legal, Compliance, and Safety. These documents are scattered
across SharePoint, the corporate intranet, and PDF repositories with no unified
search or guidance layer. Employees spend 15–30 minutes locating policy answers,
and the HR Service Desk fields ~340 policy-related inquiries per week.

The Corporate Policy Assistant Chatbot is a conversational AI system that ingests
the full policy corpus, answers employee questions with cited policy references,
generates actionable next-step checklists, and escalates to human agents when it
cannot resolve a query. It will be accessible via Microsoft Teams and an intranet
web widget. An admin console enables policy document management, testing, and
analytics.

---

## 2. Stakeholders

| Role | Name / Team | Interest |
|------|-------------|----------|
| Executive Sponsor | VP Employee Experience | Employee satisfaction, service desk cost reduction |
| Product Owner | HR Service Desk Manager | Deflection rate, answer accuracy, content validation |
| Technical Owner | Platform Engineering | Architecture, security, LLM integration standards |
| Integration Partner | IT Service Desk | Shared escalation path, ticketing integration |
| Content Partner | Facilities Management | Facilities policies, wayfinding data |
| Reviewer | Legal & Compliance | Disclaimer requirements, data handling, accuracy |
| Content Partner | Corporate Communications | Intranet integration, policy document inventory |
| Reviewer | IT Security | Data access controls, LLM data handling |
| End Users | All Employees (~8,000) | Fast, accurate policy answers |

---

## 3. Functional Requirements

### 3.1 Document Ingestion & Indexing

**FR-001:** The system SHALL ingest policy documents from SharePoint Online, the
corporate intranet CMS, and a designated cloud blob storage container for
PDF/DOCX files.

**FR-002:** The system SHALL extract text content from PDF, DOCX, and HTML
formats, preserving section headings, numbered lists, and table structures.

**FR-003:** The system SHALL chunk documents into semantically meaningful sections
and generate vector embeddings for retrieval.

**FR-004:** The system SHALL store metadata for each document: title, document ID,
category (HR, IT, Finance, Facilities, Legal, Compliance, Safety), effective date,
review date, owner, and source URL.

**FR-005:** The system SHALL support manual re-indexing of individual documents or
the full corpus via the admin console.

**FR-006:** The system SHALL maintain a version history of indexed documents and
allow administrators to view which version is currently active.

### 3.2 Conversational Interface

**FR-007:** The system SHALL accept natural language questions from employees via
a Microsoft Teams bot and a web-based chat widget embedded in the corporate
intranet.

**FR-008:** The system SHALL classify the employee's intent from their message to
determine: (a) which policy domain applies, (b) what specific information they
need, and (c) whether they need procedural guidance (how-to) or factual
information (what/who/when).

**FR-009:** The system SHALL maintain conversation context within a session so
that follow-up questions (e.g., "What about for part-time employees?") are
resolved against the prior context.

**FR-010:** The system SHALL support at least 200 concurrent conversations without
degradation.

**FR-011:** The system SHALL greet the employee by first name (retrieved from the
corporate identity provider) and optionally tailor responses based on role,
department, and location if relevant policy variations exist.

### 3.3 Answer Generation & Citation

**FR-012:** The system SHALL generate answers using retrieval-augmented generation
(RAG), retrieving relevant policy chunks and generating a natural language
response grounded in their content.

**FR-013:** Every response SHALL include a citation block listing: policy document
title, section/heading, effective date, and a direct link to the source document.

**FR-014:** The system SHALL NOT generate answers that are not grounded in indexed
policy content. If no relevant policy is found, the system SHALL respond with a
message indicating it could not find a relevant policy and offer to connect the
employee with the appropriate support team (HR, IT, or Facilities).

**FR-015:** The system SHALL include a standard disclaimer on every response
stating that the information is based on current corporate policy, is not legal
advice, and that the employee should verify the source document for the most
current version.

**FR-016:** The system SHALL detect when a query relates to a confidential HR
matter (e.g., harassment, discrimination, whistleblower) and immediately offer
direct escalation to HR without providing a chatbot-generated answer.

### 3.4 Next-Step Checklists

**FR-017:** For procedural queries (e.g., "How do I request FMLA leave?"), the
system SHALL generate a consolidated, numbered checklist of all required steps
derived from the policy.

**FR-018:** Each checklist item SHALL be classified as one of:
  - **Assisted** — the system can help complete this step (e.g., link to a form,
    open a booking page, show a map)
  - **Manual** — the employee must perform this step themselves with no system
    assistance (e.g., "Call your healthcare provider")

**FR-019:** For Assisted checklist items, the system SHALL offer the specific
assistance available:
  - Wayfinding: display a campus map link or indoor navigation directions
  - Form link: provide a deep link to the relevant form or system (e.g.,
    ServiceNow, Workday) with pre-populated fields where the API supports it
  - Scheduling: offer to generate a calendar invite or link to the relevant
    booking system
  - Contact: display the name, email, phone, and office location of the relevant
    person or team from the corporate directory

**FR-020:** For Manual checklist items, the system SHALL clearly state the action
and any relevant details (who to call, what to bring, where to go) but SHALL NOT
imply the system can perform the action.

**FR-021:** The system SHALL allow the employee to ask for more detail on any
individual checklist step.

### 3.5 Wayfinding Integration

**FR-022:** The system SHALL integrate with the corporate campus map system to
provide location-based directions when a policy step requires visiting a physical
location.

**FR-023:** The system SHALL determine wayfinding availability per campus. If
wayfinding data is not available for the employee's campus, the system SHALL fall
back to providing the building name, room number, and floor.

**FR-024:** Wayfinding responses SHALL include a link to the campus map with the
destination pre-selected.

### 3.6 Escalation

**FR-025:** At any point in a conversation, the employee SHALL be able to request
transfer to a live service desk agent (e.g., "talk to a person" or equivalent
intent).

**FR-026:** Upon escalation, the system SHALL pass the conversation transcript and
identified intent to the service desk agent via the ticketing system API so the
employee does not have to repeat themselves.

**FR-027:** The system SHALL automatically escalate if it fails to provide a
relevant answer after two consecutive attempts (confidence below threshold).

### 3.7 Feedback & Analytics

**FR-028:** After each answer, the system SHALL present thumbs-up / thumbs-down
feedback buttons with an optional free-text comment field.

**FR-029:** The admin analytics dashboard SHALL display: daily/weekly/monthly
query volume, top 20 intents, resolution rate (answered without escalation),
escalation rate, average satisfaction score, and a log of unanswered queries.

**FR-030:** The system SHALL flag queries that received negative feedback more
than 3 times on the same topic for admin review.

### 3.8 Admin Console

**FR-031:** Authorized administrators SHALL be able to upload new policy
documents, trigger re-indexing, and retire outdated documents from the active
corpus.

**FR-032:** The admin console SHALL provide a "test query" feature allowing
administrators to preview how the chatbot would answer a question before and after
a document change.

**FR-033:** The admin console SHALL display a policy coverage report showing which
policy domains have indexed content and which have gaps.

---

## 4. Non-Functional Requirements

### 4.1 Performance

**NFR-001:** The chatbot SHALL return an initial response within 5 seconds for 95%
of queries under normal load (up to 200 concurrent conversations).

**NFR-002:** Document re-indexing of a single document (up to 200 pages) SHALL
complete within 5 minutes.

**NFR-003:** Full corpus re-indexing (estimated 140 documents, ~8,000 pages) SHALL
complete within 2 hours.

### 4.2 Availability & Reliability

**NFR-004:** The chatbot SHALL maintain 99.5% uptime during business hours
(7 AM – 7 PM local time, Monday–Friday).

**NFR-005:** The system SHALL queue incoming messages during brief outages
(< 5 minutes) and process them upon recovery rather than dropping them.

**NFR-006:** If the LLM service is unavailable, the system SHALL fall back to
keyword-based search against the indexed policy corpus and clearly indicate the
response is a "basic search result, not a full answer."

### 4.3 Security & Data Handling

**NFR-007:** All access SHALL require SSO authentication via the corporate
identity provider (Microsoft Entra ID).

**NFR-008:** The system SHALL NOT store or log the content of employee queries
beyond 90 days, except aggregated/anonymized analytics.

**NFR-009:** Employee queries SHALL NOT be used to train or fine-tune any external
LLM. All LLM interactions must use an enterprise-managed LLM service within the
corporate cloud tenant with guaranteed data residency.

**NFR-010:** Role-based access control SHALL ensure: employees see only published
policy content; administrators can manage documents and view analytics; no user
can access another user's conversation history.

**NFR-011:** All data transmission SHALL use TLS 1.2 or higher.

**NFR-012:** Conversation logs and feedback data SHALL be encrypted at rest using
AES-256.

### 4.4 Scalability

**NFR-013:** The system SHALL be designed to handle a 3x increase in daily query
volume without architectural changes (target peak: 600 concurrent conversations).

**NFR-014:** The document corpus SHALL scale to at least 500 documents and 30,000
pages without re-architecture.

### 4.5 Accuracy & Quality

**NFR-015:** The system SHALL achieve a measured answer relevance score of ≥ 85%
as evaluated by a human review panel during UAT (sample of 200 queries across all
policy domains).

**NFR-016:** The system SHALL produce zero hallucinated policy statements in UAT
testing. Any answer not directly grounded in an indexed document constitutes a
defect.

### 4.6 Accessibility

**NFR-017:** The web chat widget SHALL conform to WCAG 2.1 Level AA accessibility
standards.

**NFR-018:** The chatbot SHALL support keyboard-only navigation and screen reader
compatibility.

---

## 5. Out of Scope

- Authoring or editing of policy documents (the chatbot is read-only against the
  policy corpus)
- Replacing the HR Service Desk ticketing system (ServiceNow remains the system
  of record for tickets)
- Legal advice or interpretation — the chatbot provides policy text, not legal
  counsel
- Handling of confidential HR matters (complaints, investigations) — these are
  immediately escalated to a live agent
- Voice interface (text-based chat only for v1)
- Multi-language support beyond English (future release)
- Automated policy change detection and re-indexing (manual re-index trigger for
  v1; automated pipeline planned for v2)
- Proactive policy change notifications (open question — deferred to v2 pending
  sponsor decision)

---

## 6. Assumptions

1. All employees have corporate Microsoft Entra ID SSO credentials and a
   Microsoft Teams license.
2. Policy documents are available in English and represent the current, approved
   versions. The chatbot team is not responsible for policy content accuracy.
3. The Facilities team will provide campus map data and wayfinding API access for
   at least the 3 primary campus locations (HQ, East Campus, West Campus) by
   Week 4 of the project timeline.
4. ServiceNow ITSM has a REST API available for conversation handoff and ticket
   creation.
5. An enterprise-managed LLM service is available in the corporate cloud tenant
   with sufficient quota for projected query volume.
6. The corporate directory (Microsoft Entra ID / Graph API) provides employee
   name, department, location, and manager data.
7. Approximately 8,000 employees across 12 office locations are in scope for v1.

---

## 7. Open Questions

| # | Question | Owner | Due Date | Resolution |
|---|----------|-------|----------|------------|
| 1 | Which LLM model version and deployment configuration should be used? What is the cost model and quota allocation? | Platform Engineering | Mar 27 | Open |
| 2 | Are there policy documents with restricted access (e.g., executive compensation policies) that should be excluded from the corpus? | Legal & Compliance | Mar 27 | Open |
| 3 | Should the chatbot support proactive notifications (e.g., "The PTO policy was updated — here's what changed") or is it purely reactive? | VP Employee Experience | Apr 3 | Open |
| 4 | How many campus locations have digital wayfinding data available today? What format is the data in? | Facilities Management | Apr 3 | Open |
| 5 | What is the approved approach for handling queries about policies that are under revision but not yet published? | HR Service Desk Manager | Apr 10 | Open |
| 6 | Should the system support document-level access controls (e.g., some policies only visible to managers)? | IT Security | Apr 10 | Open |
| 7 | Is there an existing knowledge base in ServiceNow that should be indexed alongside SharePoint policy docs? | IT Service Desk | Apr 10 | Open |

---

## 8. Governance Flags

| # | Flag | Requirement / Source | Conflict | Resolution |
|---|------|---------------------|----------|------------|
| 1 | **Language policy violation** | Stakeholder request (`request.md`) suggests building in Node.js | Enterprise standards permit only **Python and Go** for new projects. Node.js is prohibited. | Use Python (FastAPI) or Go. No ADR exception needed — stakeholder stated they are "open to suggestions." |
| 2 | **LLM provider policy violation** | Stakeholder request (`request.md`) suggests using "ChatGPT's API directly" | Enterprise standards require **Azure OpenAI Service** with data residency in the corporate tenant. Direct OpenAI API usage is prohibited. | Use Azure OpenAI Service. Stakeholder stated they are open to suggestions. |
| 3 | **Compute platform conflict** | BRD Section 7.2 states deployment to "existing Kubernetes (AKS) infrastructure" | Enterprise Cloud Service Preference Policy mandates **Azure Container Apps (ACA) first**. AKS requires an ADR justifying why ACA cannot meet requirements. | Escalate to Design Agent: evaluate whether ACA meets the chatbot workload requirements. If not, produce an ADR documenting the ACA limitation before selecting AKS. |
