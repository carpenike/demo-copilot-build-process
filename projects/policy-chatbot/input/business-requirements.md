# Business Requirements Document
## Corporate Policy Assistant Chatbot

| | |
|---|---|
| **Document Version** | 1.0 — Draft |
| **Date** | March 13, 2026 |
| **Prepared By** | Employee Experience & IT Services |
| **Status** | Pending Engineering Review |
| **Project Code** | EX-CHAT-2026 |

*CONFIDENTIAL — INTERNAL USE ONLY*

---

## 1. Executive Summary

Acme Corporation maintains over 140 corporate policy documents spanning HR, IT, Finance, Facilities, Legal, Compliance, and Safety. These policies are distributed across SharePoint sites, the intranet, and PDF repositories with no unified search or guidance layer. Employees routinely spend 15–30 minutes locating the correct policy document, and often resort to emailing HR or IT support with questions that are already answered in published policy.

Internal survey data shows that 62% of employees "do not know where to find" the corporate policy relevant to their situation, and the HR Service Desk fields an average of 340 policy-related inquiries per week. Many of these are repetitive (e.g., "What is the bereavement leave policy?", "How do I request a parking badge?", "What's the process for reporting a safety concern?").

This document defines the requirements for a **Corporate Policy Assistant Chatbot** — a conversational AI system that ingests the full corpus of corporate policy documents, understands employee intent, provides accurate answers grounded in policy text, and generates actionable next-step checklists tailored to the employee's situation. Where technology can assist with a next step (e.g., wayfinding to an office or facility, pre-filling a form, linking to an internal system), the chatbot will offer to do so. Where technology cannot help (e.g., "call your doctor"), the chatbot will clearly state the manual action required.

The system will integrate with the corporate intranet, Microsoft Teams, and the HR/Facilities data layer to provide contextualized, role-aware responses.

---

## 2. Business Objectives

This project is being initiated to address the following measurable business outcomes:

- Reduce HR Service Desk policy-related ticket volume by 50% within 6 months of go-live
- Reduce average employee time-to-answer for policy questions from 15–30 minutes to under 2 minutes
- Achieve 80%+ employee satisfaction rating ("helpful" or "very helpful") on chatbot interactions by Q4 2026
- Ensure 100% of chatbot answers are traceable to a specific policy document and section (no hallucinated guidance)
- Provide actionable next-step checklists for the top 50 most frequently asked policy scenarios at launch
- Enable self-service resolution of at least 70% of policy inquiries without human escalation

---

## 3. Project Scope

### 3.1 In Scope

- Conversational chat interface accessible via Microsoft Teams and a web-based intranet widget
- Ingestion and indexing of all corporate policy documents (SharePoint, intranet CMS, PDF repository)
- Intent classification to determine the employee's underlying need from natural language input
- Retrieval-augmented generation (RAG) to produce answers grounded in policy document content
- Citation of source policy document, section, and effective date in every response
- Generation of consolidated next-step checklists based on the identified policy and employee context
- Actionable assistance for next steps where technology permits:
  - Wayfinding: link to campus map / indoor navigation for facility-related steps (e.g., "Go to Room 204 in Building C")
  - Form pre-fill: deep-link into internal systems (e.g., ServiceNow, Workday) with pre-populated fields where APIs exist
  - Scheduling: offer to open a calendar invite or link to a booking system (e.g., meeting room booking, facilities appointment)
  - Contact lookup: retrieve and display the correct contact person/team from the corporate directory
- Clear indication when a next step requires manual/offline action with no technological assist available (e.g., "Call your physician", "Bring physical ID to the Security desk")
- Escalation path to a live HR or IT Service Desk agent when the chatbot cannot resolve the query or the employee requests human help
- Feedback mechanism: thumbs up/down on each response, with optional free-text comment
- Admin console for policy document management: upload, re-index, retire, and preview how the chatbot answers questions about a document
- Analytics dashboard: query volume, top intents, resolution rate, escalation rate, satisfaction scores, unanswered query log

### 3.2 Out of Scope

- Authoring or editing of policy documents (the chatbot is read-only against the policy corpus)
- Replacing the HR Service Desk ticketing system (ServiceNow remains the system of record for tickets)
- Legal advice or interpretation — the chatbot provides policy text, not legal counsel; a disclaimer is shown on every response
- Handling of confidential HR matters (e.g., complaints, investigations) — these are immediately escalated to a live agent
- Voice interface (text-based chat only for v1)
- Multi-language support beyond English (future release)
- Automated policy change detection and re-indexing (manual re-index trigger for v1; automated pipeline planned for v2)

---

## 4. Stakeholders

| Name / Team | Role | Interest | Involvement |
|---|---|---|---|
| VP Employee Experience | Executive Sponsor | Employee satisfaction, service desk cost reduction | Final sign-off |
| HR Service Desk Manager | Product Owner | Deflection rate, accuracy of policy answers | Requirements, UAT, content validation |
| Platform Engineering | Technical Owner | Architecture, security, LLM integration standards | Design, build, deploy |
| IT Service Desk | Integration Partner | Shared escalation path, ticketing integration | Integration design |
| Facilities Management | Content Partner | Facilities policies, wayfinding data | Content validation, wayfinding integration |
| Legal & Compliance | Reviewer | Disclaimer requirements, data handling, accuracy | Content review, compliance sign-off |
| Corporate Communications | Content Partner | Intranet integration, policy document inventory | Content migration, UAT |
| IT Security | Reviewer | Data access controls, LLM data handling | Security review |
| All Employees | End Users | Fast, accurate policy answers | UAT, pilot program |

---

## 5. Functional Requirements

### 5.1 Document Ingestion & Indexing

- **FR-001:** The system SHALL ingest policy documents from SharePoint Online, the corporate intranet CMS (WordPress), and a designated Azure Blob Storage container for PDF/DOCX files.
- **FR-002:** The system SHALL extract text content from PDF, DOCX, and HTML formats, preserving section headings, numbered lists, and table structures.
- **FR-003:** The system SHALL chunk documents into semantically meaningful sections and generate vector embeddings for retrieval.
- **FR-004:** The system SHALL store metadata for each document: title, document ID, category (HR, IT, Finance, Facilities, Legal, Compliance, Safety), effective date, review date, owner, and source URL.
- **FR-005:** The system SHALL support manual re-indexing of individual documents or full corpus via the admin console.
- **FR-006:** The system SHALL maintain a version history of indexed documents and allow administrators to view which version is currently active.

### 5.2 Conversational Interface

- **FR-007:** The system SHALL accept natural language questions from employees via a Microsoft Teams bot and a web-based chat widget embedded in the corporate intranet.
- **FR-008:** The system SHALL classify the employee's intent from their message to determine: (a) which policy domain applies, (b) what specific information they need, and (c) whether they need procedural guidance (how-to) or factual information (what/who/when).
- **FR-009:** The system SHALL maintain conversation context within a session so that follow-up questions (e.g., "What about for part-time employees?") are resolved against the prior context.
- **FR-010:** The system SHALL support at least 200 concurrent conversations without degradation.
- **FR-011:** The system SHALL greet the employee by first name (retrieved from Microsoft Entra ID) and optionally tailor responses based on role, department, and location if relevant policy variations exist.

### 5.3 Answer Generation & Citation

- **FR-012:** The system SHALL generate answers using retrieval-augmented generation (RAG), retrieving relevant policy chunks and generating a natural language response grounded in their content.
- **FR-013:** Every response SHALL include a citation block listing: policy document title, section/heading, effective date, and a direct link to the source document.
- **FR-014:** The system SHALL NOT generate answers that are not grounded in indexed policy content. If no relevant policy is found, the system SHALL respond with: "I wasn't able to find a policy covering that topic. Would you like me to connect you with [HR / IT / Facilities] support?"
- **FR-015:** The system SHALL include a standard disclaimer on every response: "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version."
- **FR-016:** The system SHALL detect when a query relates to a confidential HR matter (e.g., harassment, discrimination, whistleblower) and immediately offer direct escalation to HR without providing a chatbot-generated answer.

### 5.4 Next-Step Checklists

- **FR-017:** For procedural queries (e.g., "How do I request FMLA leave?", "How do I get a building access badge?"), the system SHALL generate a consolidated, numbered checklist of all required steps derived from the policy.
- **FR-018:** Each checklist item SHALL be classified as one of:
  - **Assisted** — the system can help complete this step (e.g., link to a form, open a booking page, show a map)
  - **Manual** — the employee must perform this step themselves with no system assistance (e.g., "Call your healthcare provider", "Bring two forms of ID to Security")
- **FR-019:** For **Assisted** checklist items, the system SHALL offer the specific assistance available:
  - Wayfinding: display an interactive campus map link or indoor navigation directions to the relevant office/room if wayfinding data is available for the campus
  - Form link: provide a deep link to the relevant form or system (ServiceNow, Workday, etc.) with pre-populated fields where the API supports it
  - Scheduling: offer to generate a calendar invite or link to the relevant booking system
  - Contact: display the name, email, phone, and office location of the relevant person or team from the corporate directory
- **FR-020:** For **Manual** checklist items, the system SHALL clearly state the action and any relevant details (e.g., who to call, what to bring, where to go) but SHALL NOT imply the system can perform the action.
- **FR-021:** The system SHALL allow the employee to ask for more detail on any individual checklist step.

### 5.5 Wayfinding Integration

- **FR-022:** The system SHALL integrate with the corporate campus map system to provide location-based directions when a policy step requires visiting a physical location.
- **FR-023:** The system SHALL determine wayfinding availability per campus. If wayfinding data is not available for the employee's campus, the system SHALL fall back to providing the building name, room number, and floor.
- **FR-024:** Wayfinding responses SHALL include a link to the campus map with the destination pre-selected.

### 5.6 Escalation

- **FR-025:** At any point in a conversation, the employee SHALL be able to type "talk to a person" (or equivalent intent) to be transferred to a live service desk agent.
- **FR-026:** Upon escalation, the system SHALL pass the conversation transcript and identified intent to the service desk agent via the ServiceNow API so the employee does not have to repeat themselves.
- **FR-027:** The system SHALL automatically escalate if it fails to provide a relevant answer after two consecutive attempts (confidence below threshold).

### 5.7 Feedback & Analytics

- **FR-028:** After each answer, the system SHALL present thumbs-up / thumbs-down feedback buttons with an optional free-text comment field.
- **FR-029:** The admin analytics dashboard SHALL display: daily/weekly/monthly query volume, top 20 intents, resolution rate (answered without escalation), escalation rate, average satisfaction score, and a log of unanswered queries.
- **FR-030:** The system SHALL flag queries that received negative feedback more than 3 times on the same topic for admin review.

### 5.8 Admin Console

- **FR-031:** Authorized administrators SHALL be able to upload new policy documents, trigger re-indexing, and retire outdated documents from the active corpus.
- **FR-032:** The admin console SHALL provide a "test query" feature allowing administrators to preview how the chatbot would answer a question before and after a document change.
- **FR-033:** The admin console SHALL display a policy coverage report showing which policy domains have indexed content and which have gaps.

---

## 6. Non-Functional Requirements

### 6.1 Performance

- **NFR-001:** The chatbot SHALL return an initial response within 5 seconds for 95% of queries under normal load (up to 200 concurrent conversations).
- **NFR-002:** Document re-indexing of a single document (up to 200 pages) SHALL complete within 5 minutes.
- **NFR-003:** Full corpus re-indexing (estimated 140 documents, ~8,000 pages) SHALL complete within 2 hours.

### 6.2 Availability & Reliability

- **NFR-004:** The chatbot SHALL maintain 99.5% uptime during business hours (7am–7pm local time, Monday–Friday).
- **NFR-005:** The system SHALL queue incoming messages during brief outages (< 5 minutes) and process them upon recovery rather than dropping them.
- **NFR-006:** If the LLM service is unavailable, the system SHALL fall back to keyword-based search against the indexed policy corpus and clearly indicate the response is a "basic search result, not a full answer."

### 6.3 Security & Data Handling

- **NFR-007:** All access SHALL require SSO authentication via the corporate Microsoft Entra ID identity provider.
- **NFR-008:** The system SHALL NOT store or log the content of employee queries beyond 90 days, except aggregated/anonymized analytics.
- **NFR-009:** Employee queries SHALL NOT be used to train or fine-tune any external LLM. All LLM interactions must use the Azure OpenAI Service with data residency in the corporate Azure tenant.
- **NFR-010:** Role-based access control SHALL ensure: employees see only published policy content; administrators can manage documents and view analytics; no user can access another user's conversation history.
- **NFR-011:** All data transmission SHALL use TLS 1.2 or higher.
- **NFR-012:** Conversation logs and feedback data SHALL be encrypted at rest using AES-256.

### 6.4 Scalability

- **NFR-013:** The system SHALL be designed to handle a 3x increase in daily query volume without architectural changes (target peak: 600 concurrent conversations).
- **NFR-014:** The document corpus SHALL scale to at least 500 documents and 30,000 pages without re-architecture.

### 6.5 Accuracy & Quality

- **NFR-015:** The system SHALL achieve a measured answer relevance score of ≥ 85% as evaluated by a human review panel during UAT (sample of 200 queries across all policy domains).
- **NFR-016:** The system SHALL produce zero hallucinated policy statements in UAT testing. Any answer not directly grounded in an indexed document constitutes a defect.

### 6.6 Accessibility

- **NFR-017:** The web chat widget SHALL conform to WCAG 2.1 Level AA accessibility standards.
- **NFR-018:** The chatbot SHALL support keyboard-only navigation and screen reader compatibility.

---

## 7. Assumptions and Constraints

### 7.1 Assumptions

1. All employees have corporate Microsoft Entra ID SSO credentials and a Microsoft Teams license.
2. Policy documents are available in English and represent the current, approved versions. The chatbot team is not responsible for policy content accuracy.
3. The Facilities team will provide campus map data and wayfinding API access for at least the 3 primary campus locations (HQ, East Campus, West Campus) by Week 4.
4. ServiceNow ITSM has a REST API available for conversation handoff and ticket creation.
5. Azure OpenAI Service (GPT-4o or later) is available in the corporate Azure tenant with sufficient quota for projected query volume.
6. The corporate directory (Microsoft Entra ID / Graph API) provides employee name, department, location, and manager data.
7. Approximately 8,000 employees across 12 office locations are in scope for v1.

### 7.2 Constraints

- Technology choices for this project are governed by the Platform Engineering enterprise standards. **Only Python and Go are approved for new backend services**; any deviation requires an approved Architecture Decision Record (ADR).
- The LLM provider MUST be Azure OpenAI Service — no external LLM APIs (OpenAI direct, Anthropic, etc.) are permitted due to data residency and procurement policy.
- The system must be deployable to the existing Kubernetes (AKS) infrastructure.
- All secrets and credentials must be stored in Azure Key Vault. No credentials may appear in configuration files or source code.
- The chatbot must NOT provide legal advice or HR case management. All responses must include the standard disclaimer.
- The project must be ready for a pilot launch with 500 employees by **July 15, 2026**, with full rollout by **September 1, 2026**.

---

## 8. Open Questions

| # | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| 1 | Which LLM model version and Azure OpenAI deployment configuration should be used (GPT-4o, GPT-4o-mini, etc.)? What is the cost model and quota allocation? | Platform Engineering | Mar 27 | Open |
| 2 | Are there policy documents with restricted access (e.g., executive compensation policies) that should be excluded from the corpus? | Legal & Compliance | Mar 27 | Open |
| 3 | Should the chatbot support proactive notifications (e.g., "The PTO policy was updated — here's what changed") or is it purely reactive? | VP Employee Experience | Apr 3 | Open |
| 4 | How many campus locations have digital wayfinding data available today? What format is the data in? | Facilities Management | Apr 3 | Open |
| 5 | What is the approved approach for handling queries about policies that are under revision but not yet published? | HR Service Desk Manager | Apr 10 | Open |
| 6 | Should the system support document-level access controls (e.g., some policies only visible to managers)? | IT Security | Apr 10 | Open |
| 7 | Is there an existing knowledge base in ServiceNow that should be indexed alongside SharePoint policy docs? | IT Service Desk | Apr 10 | Open |

---

## 9. Indicative Timeline

| Milestone | Target Date | Description |
|---|---|---|
| Requirements Approved | March 28, 2026 | Stakeholder sign-off on this document |
| Architecture & ADRs | April 11, 2026 | Technology decisions, RAG architecture, ADRs, API spec complete |
| Development Sprint 1 | April 14–April 25 | Auth, document ingestion pipeline, vector store, basic chat interface |
| Development Sprint 2 | April 28–May 9 | RAG answer generation, citation, intent classification, Teams bot |
| Development Sprint 3 | May 12–May 23 | Next-step checklists, wayfinding integration, escalation to ServiceNow |
| Development Sprint 4 | May 26–June 6 | Admin console, analytics dashboard, feedback system |
| Content Loading & Tuning | June 9–June 20 | Full policy corpus loaded, prompt tuning, retrieval quality tuning |
| UAT | June 23–July 11, 2026 | HR, Facilities, and employee pilot user acceptance testing |
| Pilot Launch | July 15, 2026 | 500-employee pilot group |
| Full Rollout | September 1, 2026 | All 8,000 employees |

---

## 10. Approval & Sign-Off

By signing below, stakeholders confirm they have reviewed this Business Requirements Document and agree it accurately represents the scope and requirements for the Corporate Policy Assistant Chatbot.

| Name | Role | Signature | Date |
|---|---|---|---|
| | VP Employee Experience | | |
| | HR Service Desk Manager | | |
| | Platform Engineering Lead | | |
| | IT Security Lead | | |
| | Legal & Compliance | | |
