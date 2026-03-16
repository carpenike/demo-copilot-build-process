# User Stories: Policy Chatbot

> **Version:** 1.0
> **Status:** Draft
> **Date:** 2026-03-16
> **Produced by:** Requirements Agent

---

## Story Index

| ID | Title | Priority | FR Coverage | Status |
|----|-------|----------|-------------|--------|
| US-001 | Ask a policy question | High | FR-007, FR-008, FR-009, FR-012, FR-013, FR-014, FR-015 | Draft |
| US-002 | Receive a next-step checklist | High | FR-017, FR-018, FR-019, FR-020, FR-021 | Draft |
| US-003 | Get wayfinding directions | Medium | FR-022, FR-023, FR-024 | Draft |
| US-004 | Escalate to a live agent | High | FR-025, FR-026, FR-027 | Draft |
| US-005 | Provide feedback on an answer | Medium | FR-028, FR-030 | Draft |
| US-006 | Confidential topic detection | High | FR-016 | Draft |
| US-007 | Personalized greeting and context | Medium | FR-011 | Draft |
| US-008 | Upload and re-index a policy document | High | FR-001, FR-002, FR-005, FR-006, FR-031 | Draft |
| US-009 | Test chatbot answers as admin | Medium | FR-032 | Draft |
| US-010 | View analytics dashboard | Medium | FR-029, FR-030 | Draft |
| US-011 | View policy coverage report | Medium | FR-033 | Draft |
| US-012 | Ingest and chunk policy documents | High | FR-001, FR-002, FR-003, FR-004 | Draft |
| US-013 | Fallback when LLM is unavailable | Medium | NFR-006 | Draft |
| US-014 | Follow-up question in context | High | FR-009 | Draft |

---

## Stories

---

### US-001: Ask a Policy Question

**Priority:** High
**Related requirements:** FR-007, FR-008, FR-009, FR-012, FR-013, FR-014, FR-015

**Story:**
> As an **employee**,
> I want to **ask a natural language question about a corporate policy**,
> so that **I get an accurate, cited answer without searching through multiple document repositories**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee asks a question with a matching policy
  Given the employee is authenticated via Microsoft Entra ID SSO
  And the policy corpus has been indexed and contains a relevant document
  When the employee submits "What is the bereavement leave policy?"
  Then the system returns a natural language answer grounded in the indexed policy content
  And the response includes a citation block with policy title, section, effective date, and source link
  And the response includes the standard legal disclaimer

Scenario: Employee asks a question with no matching policy
  Given the employee is authenticated via Microsoft Entra ID SSO
  And no indexed policy document covers the topic
  When the employee submits "What is the policy on bringing pets to the office?"
  Then the system responds with "I wasn't able to find a policy covering that topic."
  And the system offers to connect the employee with HR, IT, or Facilities support

Scenario: Employee uses the Teams bot
  Given the employee is authenticated and in Microsoft Teams
  When the employee sends a message to the Policy Assistant bot
  Then the system accepts the message and returns a response within the Teams interface

Scenario: Employee uses the intranet widget
  Given the employee is authenticated and on the corporate intranet
  When the employee types a question in the web chat widget
  Then the system accepts the message and returns a response within the widget
```

**Out of scope for this story:**
- Follow-up questions (see US-014)
- Next-step checklists (see US-002)

**Dependencies:**
- Depends on: US-012 (document ingestion must be complete)

---

### US-002: Receive a Next-Step Checklist

**Priority:** High
**Related requirements:** FR-017, FR-018, FR-019, FR-020, FR-021

**Story:**
> As an **employee**,
> I want to **receive a numbered checklist of actions I need to take after learning about a policy**,
> so that **I know exactly what steps to follow and which ones the system can help me with**.

**Acceptance Criteria:**

```gherkin
Scenario: Procedural query returns a checklist with assisted and manual steps
  Given the employee asks "How do I request parental leave?"
  And the parental leave policy defines a multi-step process
  When the system generates the response
  Then the response includes a numbered checklist of all required steps
  And each step is classified as either "Assisted" or "Manual"
  And Assisted steps include actionable links (form links, booking system, contact info)
  And Manual steps clearly describe the offline action required without implying the system can perform it

Scenario: Employee asks for detail on a specific checklist step
  Given the employee has received a checklist response
  When the employee asks "Tell me more about step 3"
  Then the system provides additional detail about that specific step from the policy
  And the response maintains the context of the original checklist

Scenario: Factual query does not generate a checklist
  Given the employee asks "What is the maximum number of PTO days per year?"
  When the system generates the response
  Then the response provides the factual answer with citation
  And no checklist is generated because the query is informational, not procedural
```

**Out of scope for this story:**
- Wayfinding-specific assistance (see US-003)

**Dependencies:**
- Depends on: US-001 (basic Q&A must work)

---

### US-003: Get Wayfinding Directions

**Priority:** Medium
**Related requirements:** FR-022, FR-023, FR-024

**Story:**
> As an **employee**,
> I want to **get directions to a physical location when a policy step requires visiting a specific office or room**,
> so that **I can find the right place on campus without asking around**.

**Acceptance Criteria:**

```gherkin
Scenario: Wayfinding data is available for the employee's campus
  Given the employee's campus has wayfinding data integrated
  And a checklist step requires visiting a physical location (e.g., "Go to Security in Room 204, Building C")
  When the system generates the checklist step
  Then the step includes a link to the campus map with the destination pre-selected
  And the step is classified as "Assisted"

Scenario: Wayfinding data is not available for the employee's campus
  Given the employee's campus does NOT have wayfinding data integrated
  And a checklist step requires visiting a physical location
  When the system generates the checklist step
  Then the step falls back to displaying the building name, room number, and floor
  And no map link is provided

Scenario: Employee explicitly asks for directions
  Given the employee asks "Where is the HR benefits office?"
  When wayfinding data is available for their campus
  Then the system provides the building, room, and floor information
  And includes a campus map link with the destination pre-selected
```

**Dependencies:**
- Depends on: US-002 (checklists must work)
- Depends on: Facilities team providing wayfinding API access (Assumption #3)

---

### US-004: Escalate to a Live Agent

**Priority:** High
**Related requirements:** FR-025, FR-026, FR-027

**Story:**
> As an **employee**,
> I want to **be transferred to a live service desk agent when the chatbot can't help me or I prefer human assistance**,
> so that **I get my question answered without starting over**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee explicitly requests a human agent
  Given the employee is in an active conversation
  When the employee types "talk to a person" or expresses equivalent intent
  Then the system initiates escalation to a live service desk agent
  And the conversation transcript and identified intent are passed to the agent via the ServiceNow API

Scenario: System auto-escalates after repeated low-confidence answers
  Given the system has failed to provide a relevant answer (confidence below threshold)
  And this is the second consecutive low-confidence response
  When the system generates the next response
  Then the system automatically offers escalation to a live agent
  And includes the conversation transcript and intent in the ServiceNow handoff

Scenario: Escalation preserves conversation context
  Given an escalation is triggered (manual or automatic)
  When the service desk agent receives the escalation
  Then the agent can see the full conversation transcript
  And the agent can see the identified intent and policy domain
  And the employee does not have to repeat their question
```

**Out of scope for this story:**
- Confidential HR matter detection (see US-006)

**Dependencies:**
- Depends on: ServiceNow REST API availability (Assumption #4)

---

### US-005: Provide Feedback on an Answer

**Priority:** Medium
**Related requirements:** FR-028, FR-030

**Story:**
> As an **employee**,
> I want to **rate the chatbot's answer and optionally leave a comment**,
> so that **the policy team can track quality and improve the system over time**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee gives positive feedback
  Given the system has provided an answer
  When the employee clicks the thumbs-up button
  Then the feedback is recorded and associated with the query and response

Scenario: Employee gives negative feedback with a comment
  Given the system has provided an answer
  When the employee clicks the thumbs-down button
  And enters an optional free-text comment
  Then the feedback and comment are recorded and associated with the query and response

Scenario: Repeated negative feedback triggers admin alert
  Given a specific topic has received negative feedback more than 3 times
  When the threshold is crossed
  Then the topic is flagged in the admin dashboard for review
```

**Dependencies:**
- Depends on: US-001 (answers must be generated before feedback can be collected)

---

### US-006: Confidential Topic Detection

**Priority:** High
**Related requirements:** FR-016

**Story:**
> As an **employee**,
> I want the **chatbot to recognize when my question involves a confidential HR matter and immediately connect me with HR**,
> so that **sensitive issues are handled by a human and not answered by an AI**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee asks about a confidential topic
  Given the employee submits a query related to harassment, discrimination, or whistleblower concerns
  When the system classifies the intent
  Then the system does NOT generate a chatbot answer
  And the system offers direct escalation to HR with a supportive message
  And no chatbot-generated policy content is displayed for this query

Scenario: Edge case — ambiguous query that could be confidential
  Given the employee submits a query that is ambiguous but may relate to a confidential matter
  When the system classifies the intent with low confidence on the confidential category
  Then the system asks a clarifying question before proceeding
  And does not generate a policy answer until the intent is clarified
```

**Out of scope for this story:**
- General escalation flow (see US-004)

**Dependencies:**
- None (can be built independently)

---

### US-007: Personalized Greeting and Context

**Priority:** Medium
**Related requirements:** FR-011

**Story:**
> As an **employee**,
> I want the **chatbot to greet me by name and tailor responses based on my role, department, and location**,
> so that **I get relevant answers without having to specify my context manually**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee starts a conversation
  Given the employee is authenticated via Microsoft Entra ID SSO
  When the employee opens the chatbot for the first time in a session
  Then the system greets the employee by first name (retrieved from Microsoft Entra ID)

Scenario: Policy varies by location
  Given the employee is based at West Campus
  And the parking policy has location-specific rules
  When the employee asks "How do I get a parking badge?"
  Then the response is tailored to West Campus parking procedures
  And the citation references the location-specific section of the policy

Scenario: Policy varies by role
  Given the employee is a people manager
  And the PTO approval policy has different rules for managers
  When the employee asks about the PTO approval process
  Then the response includes manager-specific guidance
```

**Dependencies:**
- Depends on: Microsoft Entra ID / Graph API access (Assumption #6)

---

### US-008: Upload and Re-index a Policy Document

**Priority:** High
**Related requirements:** FR-001, FR-002, FR-005, FR-006, FR-031

**Story:**
> As a **policy administrator**,
> I want to **upload a new or updated policy document and trigger re-indexing**,
> so that **the chatbot's answers reflect the latest published policies**.

**Acceptance Criteria:**

```gherkin
Scenario: Admin uploads a new PDF policy document
  Given the admin is authenticated and has the administrator role
  When the admin uploads a PDF file via the admin console
  And triggers re-indexing for that document
  Then the system extracts text from the PDF preserving structure
  And chunks the document and generates vector embeddings
  And stores metadata (title, category, effective date, owner, source URL)
  And the document becomes available in the chatbot's active corpus

Scenario: Admin re-indexes an updated document
  Given a policy document has been revised
  When the admin uploads the new version and triggers re-indexing
  Then the previous version is retained in version history
  And the new version becomes the active version
  And the admin can view which version is currently active

Scenario: Admin retires an outdated document
  Given a policy document is no longer in effect
  When the admin marks the document as retired via the admin console
  Then the document is removed from the active corpus
  And the chatbot no longer references it in answers
  And the document remains available in version history for audit purposes

Scenario: Unauthorized user attempts admin actions
  Given a user without the administrator role
  When they attempt to upload, re-index, or retire a document
  Then the system denies the action with a permission denied response
```

**Dependencies:**
- Depends on: US-012 (ingestion pipeline must exist)

---

### US-009: Test Chatbot Answers as Admin

**Priority:** Medium
**Related requirements:** FR-032

**Story:**
> As a **policy administrator**,
> I want to **preview how the chatbot would answer a question before and after a document change**,
> so that **I can verify the impact of content changes before they affect employees**.

**Acceptance Criteria:**

```gherkin
Scenario: Admin tests a query against the current corpus
  Given the admin is on the admin console
  When the admin enters a test query
  Then the system shows the chatbot's response as an employee would see it
  And includes citations and checklist if applicable

Scenario: Admin compares before/after a document change
  Given the admin has uploaded a new version of a document but not yet activated it
  When the admin enters a test query
  Then the system shows side-by-side responses: one against the current active corpus AND one against the corpus with the pending document change
```

**Dependencies:**
- Depends on: US-008 (document management must exist)
- Depends on: US-001 (query answering must work)

---

### US-010: View Analytics Dashboard

**Priority:** Medium
**Related requirements:** FR-029, FR-030

**Story:**
> As a **policy administrator**,
> I want to **view analytics about chatbot usage, satisfaction, and gaps**,
> so that **I can identify areas for improvement and measure the system's impact**.

**Acceptance Criteria:**

```gherkin
Scenario: Admin views the analytics dashboard
  Given the admin is authenticated with the administrator role
  When the admin opens the analytics dashboard
  Then the dashboard displays: daily, weekly, and monthly query volume
  And shows the top 20 intents by frequency
  And shows overall resolution rate (answered without escalation)
  And shows escalation rate
  And shows average satisfaction score
  And provides a filterable log of unanswered queries

Scenario: Admin reviews flagged topics
  Given one or more topics have received negative feedback more than 3 times
  When the admin views the flagged topics section
  Then each flagged topic is listed with the query text, response given, feedback count, and sample comments
```

**Dependencies:**
- Depends on: US-005 (feedback collection must exist)
- Depends on: US-001 (query answering must work)

---

### US-011: View Policy Coverage Report

**Priority:** Medium
**Related requirements:** FR-033

**Story:**
> As a **policy administrator**,
> I want to **see which policy domains have indexed content and which have gaps**,
> so that **I can prioritize document uploads and ensure complete coverage**.

**Acceptance Criteria:**

```gherkin
Scenario: Admin views the policy coverage report
  Given the admin is on the admin console
  When the admin opens the policy coverage report
  Then the report shows all policy domains (HR, IT, Finance, Facilities, Legal, Compliance, Safety)
  And for each domain, shows the count of indexed documents, the last updated date, and any domains with zero documents
  And domains with zero coverage are highlighted as gaps
```

**Dependencies:**
- Depends on: US-008 (documents must be uploadable)

---

### US-012: Ingest and Chunk Policy Documents

**Priority:** High
**Related requirements:** FR-001, FR-002, FR-003, FR-004

**Story:**
> As the **system**,
> I need to **ingest policy documents from multiple sources, extract text, chunk into semantic sections, and generate vector embeddings**,
> so that **the RAG pipeline can retrieve relevant policy content for answering questions**.

**Acceptance Criteria:**

```gherkin
Scenario: Ingest a PDF document
  Given a PDF policy document is stored in the designated Azure Blob Storage container
  When the ingestion pipeline processes the document
  Then text is extracted preserving section headings, numbered lists, and table structures
  And the document is chunked into semantically meaningful sections
  And vector embeddings are generated for each chunk
  And metadata is stored: title, document ID, category, effective date, review date, owner, source URL

Scenario: Ingest an HTML document from the intranet CMS
  Given an HTML policy page exists on the corporate intranet (WordPress)
  When the ingestion pipeline processes the page
  Then text is extracted preserving structural elements
  And the document is chunked and embedded identically to PDF documents

Scenario: Ingest a DOCX document from SharePoint
  Given a DOCX policy document is stored in SharePoint Online
  When the ingestion pipeline processes the document
  Then text is extracted preserving structural elements
  And the document is chunked and embedded identically to other formats
```

**Dependencies:**
- None (foundational capability)

---

### US-013: Fallback When LLM Is Unavailable

**Priority:** Medium
**Related requirements:** NFR-006

**Story:**
> As an **employee**,
> I want to **still get basic policy search results even when the AI service is down**,
> so that **I'm not completely blocked from finding information**.

**Acceptance Criteria:**

```gherkin
Scenario: LLM service is unavailable
  Given the Azure OpenAI Service endpoint is unreachable or returning errors
  When the employee submits a query
  Then the system falls back to keyword-based search against the indexed policy corpus
  And the response is clearly labeled as a "basic search result, not a full answer"
  And the system suggests the employee try again later for a complete answer or escalate to a live agent
```

**Dependencies:**
- Depends on: US-012 (indexed corpus must exist for keyword search)

---

### US-014: Follow-Up Question in Context

**Priority:** High
**Related requirements:** FR-009

**Story:**
> As an **employee**,
> I want to **ask follow-up questions without repeating context**,
> so that **I can drill deeper into a topic naturally**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee asks a follow-up question
  Given the employee asked "What is the parental leave policy?"
  And received an answer about the general parental leave policy
  When the employee follows up with "What about for part-time employees?"
  Then the system resolves the follow-up against the prior conversation context
  And provides the parental leave policy details specific to part-time employees
  And includes appropriate citations

Scenario: Employee starts a new topic mid-conversation
  Given the employee has been asking about parental leave
  When the employee asks "How do I get a parking badge?"
  Then the system recognizes this as a new topic
  And provides a fresh answer about parking badges without parental leave context
```

**Dependencies:**
- Depends on: US-001 (basic Q&A must work)
