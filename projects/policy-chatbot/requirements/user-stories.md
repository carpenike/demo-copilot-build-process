# User Stories: Policy Chatbot

> **Version:** 1.0
> **Status:** Draft
> **Date:** 2026-03-17
> **Produced by:** Requirements Agent

---

## Story Index

| ID | Title | Priority | FR Coverage | Status |
|----|-------|----------|-------------|--------|
| US-001 | Ask a policy question and get a cited answer | High | FR-007, FR-008, FR-012, FR-013, FR-014, FR-015 | Draft |
| US-002 | Follow-up question within conversation context | High | FR-009 | Draft |
| US-003 | Receive a next-step checklist for a procedural query | High | FR-017, FR-018, FR-019, FR-020, FR-021 | Draft |
| US-004 | Get wayfinding directions for a physical location step | Medium | FR-022, FR-023, FR-024 | Draft |
| US-005 | Escalate to a live service desk agent | High | FR-025, FR-026, FR-027 | Draft |
| US-006 | Confidential HR matter detection and escalation | High | FR-016 | Draft |
| US-007 | Provide feedback on a chatbot response | Medium | FR-028, FR-030 | Draft |
| US-008 | Personalized greeting and role-aware responses | Medium | FR-011 | Draft |
| US-009 | Upload and index a new policy document | High | FR-001, FR-002, FR-003, FR-004, FR-005, FR-031 | Draft |
| US-010 | Re-index the full policy corpus | Medium | FR-005, FR-003, FR-006 | Draft |
| US-011 | Test chatbot answers before publishing a document change | High | FR-032 | Draft |
| US-012 | View policy coverage report | Medium | FR-033 | Draft |
| US-013 | View analytics dashboard | Medium | FR-029 | Draft |
| US-014 | Retire an outdated policy document | Medium | FR-031, FR-006 | Draft |
| US-015 | Keyword fallback when LLM is unavailable | Medium | NFR-006 | Draft |
| US-016 | Authenticate via corporate SSO | High | NFR-007, NFR-010 | Draft |

---

## Stories

---

### US-001: Ask a Policy Question and Get a Cited Answer

**Priority:** High
**Related requirements:** FR-007, FR-008, FR-012, FR-013, FR-014, FR-015

**Story:**
> As an **employee**,
> I want to **ask a natural language question about corporate policy via Teams or
> the intranet chat widget**,
> so that **I get an accurate answer grounded in the actual policy document,
> with a citation I can verify, instead of searching through multiple systems**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee asks a question covered by an indexed policy
  Given the employee is authenticated via SSO
  And the policy corpus contains a document covering "bereavement leave"
  When the employee types "What is the bereavement leave policy?"
  Then the system returns an answer grounded in the bereavement leave policy
  And the response includes a citation block with document title, section, effective date, and source link
  And the response includes the standard disclaimer

Scenario: Employee asks a question not covered by any indexed policy
  Given the employee is authenticated via SSO
  And no indexed policy covers "bring your pet to work day"
  When the employee types "Can I bring my dog to the office?"
  Then the system responds that it could not find a relevant policy
  And the system offers to connect the employee with the appropriate support team

Scenario: Employee uses the web chat widget on the intranet
  Given the employee is authenticated via SSO
  And the employee is on the corporate intranet page
  When the employee opens the chat widget and types a policy question
  Then the system processes the question and returns a cited answer
  And the interaction is functionally identical to the Teams experience

Scenario: System classifies intent correctly
  Given the employee asks "How do I request FMLA leave?"
  When the system classifies the intent
  Then it identifies the policy domain as "HR"
  And it identifies the query type as "procedural guidance"
```

**Out of scope for this story:**
- Checklist generation (covered in US-003)
- Wayfinding integration (covered in US-004)

**Dependencies:**
- Depends on: US-009 (policy documents must be ingested first)
- Depends on: US-016 (SSO authentication)

---

### US-002: Follow-Up Question Within Conversation Context

**Priority:** High
**Related requirements:** FR-009

**Story:**
> As an **employee**,
> I want to **ask follow-up questions that reference my previous question without
> restating the full context**,
> so that **the conversation feels natural and I can drill into details
> efficiently**.

**Acceptance Criteria:**

```gherkin
Scenario: Follow-up question resolved against prior context
  Given the employee previously asked "What is the parental leave policy?"
  And the system returned the parental leave policy answer
  When the employee asks "What about for part-time employees?"
  Then the system interprets the question in the context of parental leave
  And returns the parental leave policy as it applies to part-time employees

Scenario: Context is maintained within a session
  Given the employee is in an active conversation session
  When the employee asks three sequential follow-up questions on the same topic
  Then each answer correctly references the established context

Scenario: New topic resets context appropriately
  Given the employee previously asked about parental leave
  When the employee asks "What's the travel expense reimbursement process?"
  Then the system recognizes this as a new topic
  And returns the travel expense policy without confusing it with parental leave context
```

**Out of scope for this story:**
- Cross-session context persistence (sessions are independent)

**Dependencies:**
- Depends on: US-001

---

### US-003: Receive a Next-Step Checklist for a Procedural Query

**Priority:** High
**Related requirements:** FR-017, FR-018, FR-019, FR-020, FR-021

**Story:**
> As an **employee**,
> I want to **receive a numbered checklist of all required steps when I ask a
> "how do I" question**,
> so that **I know exactly what to do, in what order, and which steps the system
> can help me with**.

**Acceptance Criteria:**

```gherkin
Scenario: Procedural query returns a checklist with assisted and manual items
  Given the employee asks "How do I request FMLA leave?"
  And the FMLA policy defines 5 procedural steps
  When the system generates the response
  Then the response includes a numbered checklist of all 5 steps
  And each step is classified as either "Assisted" or "Manual"
  And Assisted steps include actionable links (form links, booking links, contacts)
  And Manual steps clearly state the required action without implying system assistance

Scenario: Employee asks for more detail on a checklist step
  Given the employee received a checklist with 5 steps
  When the employee asks "Tell me more about step 3"
  Then the system provides expanded detail on step 3
  And the response remains grounded in the source policy

Scenario: Assisted step provides a deep link to a form
  Given a checklist step is classified as Assisted
  And the step involves submitting a form in Workday
  When the system displays the step
  Then it includes a deep link to the Workday form

Scenario: Manual step is clearly distinguished
  Given a checklist step requires calling a healthcare provider
  When the system displays the step
  Then it states "Call your healthcare provider" with relevant contact details
  And it does NOT offer to make the call or imply automation
```

**Out of scope for this story:**
- Wayfinding links in checklist steps (covered in US-004)

**Dependencies:**
- Depends on: US-001

---

### US-004: Get Wayfinding Directions for a Physical Location Step

**Priority:** Medium
**Related requirements:** FR-022, FR-023, FR-024

**Story:**
> As an **employee**,
> I want to **receive directions to a physical location when a policy step
> requires me to visit a specific office or building**,
> so that **I can find the right place without guessing**.

**Acceptance Criteria:**

```gherkin
Scenario: Wayfinding data is available for the employee's campus
  Given the employee is located at HQ campus
  And wayfinding data is available for HQ campus
  And a checklist step says "Visit the Security desk in Building C, Room 204"
  When the system displays the step
  Then it includes a link to the campus map with Building C, Room 204 pre-selected

Scenario: Wayfinding data is not available for the employee's campus
  Given the employee is located at a satellite office without wayfinding data
  And a checklist step requires visiting a physical location
  When the system displays the step
  Then it provides the building name, room number, and floor as plain text
  And it does NOT display a broken or empty map link

Scenario: Multiple wayfinding steps in one checklist
  Given a procedural answer includes two steps that require visiting different locations
  When the system displays the checklist
  Then each location step includes its own wayfinding link or address details
```

**Dependencies:**
- Depends on: US-003
- Depends on: Facilities team providing wayfinding API access

---

### US-005: Escalate to a Live Service Desk Agent

**Priority:** High
**Related requirements:** FR-025, FR-026, FR-027

**Story:**
> As an **employee**,
> I want to **be transferred to a live service desk agent when I need human help**,
> so that **I don't get stuck in a chatbot loop when my question is too complex or
> I simply prefer a person**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee explicitly requests a live agent
  Given the employee is in an active conversation
  When the employee types "talk to a person"
  Then the system acknowledges the request
  And transfers the conversation to a live HR or IT service desk agent
  And passes the conversation transcript and identified intent to the agent via the ticketing system API

Scenario: Employee uses equivalent phrasing
  Given the employee is in an active conversation
  When the employee types "I need to speak to someone" or "connect me with HR"
  Then the system recognizes the escalation intent
  And initiates the transfer

Scenario: Automatic escalation after two failed attempts
  Given the system provided an answer with confidence below the threshold
  And the employee asked a follow-up that also falls below the confidence threshold
  When the second low-confidence response is generated
  Then the system automatically offers escalation to a live agent
  And the employee can accept or decline

Scenario: Conversation transcript is passed to the agent
  Given the employee has exchanged 4 messages with the chatbot
  When the escalation is initiated
  Then the service desk agent receives the full conversation transcript
  And the agent receives the system's best guess at the employee's intent
  And the employee does not have to repeat their question
```

**Dependencies:**
- Depends on: ServiceNow REST API availability for handoff

---

### US-006: Confidential HR Matter Detection and Escalation

**Priority:** High
**Related requirements:** FR-016

**Story:**
> As an **employee**,
> I want the **chatbot to recognize when my question involves a sensitive or
> confidential HR matter and immediately route me to a human**,
> so that **I am not given an automated response for something that requires
> confidential handling**.

**Acceptance Criteria:**

```gherkin
Scenario: Query triggers confidential matter detection
  Given the employee asks "I want to report harassment in my team"
  When the system classifies the intent
  Then it detects the query relates to a confidential HR matter
  And it does NOT generate a chatbot answer
  And it immediately offers direct escalation to HR with a message like "This sounds like it may be a sensitive matter. Let me connect you directly with HR."

Scenario: Discrimination-related query is detected
  Given the employee asks about filing a discrimination complaint
  When the system classifies the intent
  Then it routes the employee to HR without providing policy text

Scenario: Whistleblower query is detected
  Given the employee asks about reporting fraud or ethical violations
  When the system classifies the intent
  Then it routes the employee to the appropriate confidential channel

Scenario: Non-confidential HR query is handled normally
  Given the employee asks "What's the dress code policy?"
  When the system classifies the intent
  Then it identifies this as a standard HR policy question
  And returns a normal cited answer
```

**Out of scope for this story:**
- Case management or tracking of confidential matters (handled by HR systems)

---

### US-007: Provide Feedback on a Chatbot Response

**Priority:** Medium
**Related requirements:** FR-028, FR-030

**Story:**
> As an **employee**,
> I want to **rate each chatbot response as helpful or unhelpful and optionally
> leave a comment**,
> so that **the team can improve answer quality over time**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee gives thumbs-up feedback
  Given the system has just displayed an answer
  When the employee clicks the thumbs-up button
  Then the feedback is recorded against that specific response
  And no further action is required from the employee

Scenario: Employee gives thumbs-down with a comment
  Given the system has just displayed an answer
  When the employee clicks the thumbs-down button
  And enters a free-text comment "The policy has changed, this is outdated"
  Then the feedback and comment are recorded against that response

Scenario: Repeated negative feedback flags a topic for review
  Given queries about "remote work policy" have received negative feedback more than 3 times
  When an administrator views the admin console
  Then the "remote work policy" topic is flagged for review
  And the negative feedback entries and comments are visible
```

**Dependencies:**
- Depends on: US-001

---

### US-008: Personalized Greeting and Role-Aware Responses

**Priority:** Medium
**Related requirements:** FR-011

**Story:**
> As an **employee**,
> I want the **chatbot to greet me by name and tailor answers to my role,
> department, and location when relevant**,
> so that **I get the most relevant information without having to specify my
> context manually**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee is greeted by first name
  Given the employee is authenticated via SSO
  And their profile in the corporate directory lists their first name as "Sarah"
  When the employee opens a new conversation
  Then the chatbot greets them as "Sarah"

Scenario: Policy varies by employee location
  Given the parking policy differs between HQ and East Campus
  And the employee's profile indicates they are at East Campus
  When the employee asks "How do I get a parking badge?"
  Then the system returns the East Campus parking policy
  And does NOT return the HQ version unless asked

Scenario: Policy varies by role
  Given the expense approval policy has different limits for managers vs. individual contributors
  And the employee's profile indicates they are a manager
  When the employee asks "What's the expense approval limit?"
  Then the system returns the manager-specific limit
```

**Dependencies:**
- Depends on: Microsoft Entra ID / Graph API providing role, department, and location data

---

### US-009: Upload and Index a New Policy Document

**Priority:** High
**Related requirements:** FR-001, FR-002, FR-003, FR-004, FR-005, FR-031

**Story:**
> As a **policy administrator**,
> I want to **upload a new policy document to the system and trigger indexing**,
> so that **the chatbot can answer questions about the new policy**.

**Acceptance Criteria:**

```gherkin
Scenario: Administrator uploads a PDF policy document
  Given the administrator is authenticated and has admin role
  When they upload a PDF file via the admin console
  And provide metadata (title, category, effective date, owner)
  Then the system ingests the document
  And extracts text preserving headings, lists, and tables
  And chunks the document and generates vector embeddings
  And the document becomes available in the chatbot's knowledge base

Scenario: Administrator uploads a DOCX policy document
  Given the administrator uploads a DOCX file
  When ingestion completes
  Then the document content is correctly extracted and indexed

Scenario: Upload is rejected for unsupported format
  Given the administrator attempts to upload a .pptx file
  When the upload is submitted
  Then the system rejects the upload with a message listing supported formats (PDF, DOCX, HTML)

Scenario: Metadata is stored correctly
  Given the administrator uploads a document with metadata
  When the document is indexed
  Then the system stores: title, document ID, category, effective date, review date, owner, and source URL
  And this metadata appears in the admin console document list
```

**Dependencies:**
- Depends on: US-016 (admin must be authenticated and authorized)

---

### US-010: Re-Index the Full Policy Corpus

**Priority:** Medium
**Related requirements:** FR-005, FR-003, FR-006

**Story:**
> As a **policy administrator**,
> I want to **trigger a full re-index of all policy documents**,
> so that **embeddings are regenerated with any updated chunking or embedding
> configuration**.

**Acceptance Criteria:**

```gherkin
Scenario: Full corpus re-indexing completes within SLA
  Given the corpus contains 140 documents (~8,000 pages)
  When the administrator triggers a full re-index from the admin console
  Then re-indexing completes within 2 hours
  And the chatbot continues serving answers from the previous index during re-indexing
  And the new index replaces the old one upon completion

Scenario: Administrator views indexing progress
  Given a full re-index is in progress
  When the administrator views the admin console
  Then they see a progress indicator (documents processed / total)

Scenario: Re-indexing preserves version history
  Given a document was previously indexed at version 1
  When the document is re-indexed at version 2
  Then version history shows both versions
  And the administrator can see which version is currently active
```

---

### US-011: Test Chatbot Answers Before Publishing a Document Change

**Priority:** High
**Related requirements:** FR-032

**Story:**
> As a **policy administrator**,
> I want to **preview how the chatbot answers questions about a document before
> and after a change**,
> so that **I can verify answer quality before the change goes live**.

**Acceptance Criteria:**

```gherkin
Scenario: Administrator tests a query against current and updated document
  Given the administrator has uploaded an updated version of a policy document
  And the update has not yet been published to the live corpus
  When the administrator enters a test query in the admin console
  Then the system shows the answer as it would appear with the current live document
  And the system shows the answer as it would appear with the updated document
  And the administrator can compare the two side-by-side

Scenario: Administrator approves the update after testing
  Given the administrator has reviewed test query results
  When they approve the document update
  Then the updated document is published to the live corpus
  And the chatbot begins using the new version for all subsequent queries
```

**Dependencies:**
- Depends on: US-009

---

### US-012: View Policy Coverage Report

**Priority:** Medium
**Related requirements:** FR-033

**Story:**
> As a **policy administrator**,
> I want to **see which policy domains have indexed content and where gaps exist**,
> so that **I can prioritize uploading missing documents**.

**Acceptance Criteria:**

```gherkin
Scenario: Coverage report shows all policy domains
  Given the system has 7 policy domains (HR, IT, Finance, Facilities, Legal, Compliance, Safety)
  When the administrator views the coverage report
  Then each domain is listed with the count of indexed documents
  And domains with zero documents are highlighted as gaps

Scenario: Report updates after a new document is indexed
  Given the Legal domain had 0 indexed documents
  When the administrator uploads and indexes a Legal policy
  Then the coverage report shows Legal with 1 document
```

---

### US-013: View Analytics Dashboard

**Priority:** Medium
**Related requirements:** FR-029

**Story:**
> As a **policy administrator**,
> I want to **view analytics on chatbot usage, satisfaction, and escalation
> rates**,
> so that **I can measure ROI and identify areas for improvement**.

**Acceptance Criteria:**

```gherkin
Scenario: Dashboard displays key metrics
  Given the chatbot has been live for 1 week with recorded interactions
  When the administrator opens the analytics dashboard
  Then the dashboard displays: daily/weekly/monthly query volume, top 20 intents, resolution rate, escalation rate, and average satisfaction score

Scenario: Unanswered query log is available
  Given several queries received no relevant answer
  When the administrator views the unanswered query log
  Then each entry shows the query text, timestamp, and the domain the system attempted to match

Scenario: Date range filter works correctly
  Given the administrator wants to see metrics for a specific week
  When they select a date range filter
  Then only data within that range is displayed
```

---

### US-014: Retire an Outdated Policy Document

**Priority:** Medium
**Related requirements:** FR-031, FR-006

**Story:**
> As a **policy administrator**,
> I want to **retire a policy document so it is no longer used for chatbot
> answers**,
> so that **employees don't receive outdated information**.

**Acceptance Criteria:**

```gherkin
Scenario: Administrator retires a document
  Given the document "Travel Policy v2.0" is currently active in the corpus
  When the administrator marks it as retired via the admin console
  Then the document is removed from the active corpus
  And the chatbot no longer references it in answers
  And the document remains in version history for audit purposes

Scenario: Retired document does not appear in answers
  Given the "Travel Policy v2.0" has been retired
  When an employee asks about travel reimbursement
  Then the system does NOT cite the retired document
  And if a replacement document exists, it cites the replacement instead
```

---

### US-015: Keyword Fallback When LLM Is Unavailable

**Priority:** Medium
**Related requirements:** NFR-006

**Story:**
> As an **employee**,
> I want to **still get useful results from the chatbot even when the LLM service
> is down**,
> so that **I'm not completely blocked from finding policy information**.

**Acceptance Criteria:**

```gherkin
Scenario: LLM service is unavailable
  Given the LLM service is experiencing an outage
  When the employee asks a policy question
  Then the system performs a keyword-based search against the indexed corpus
  And returns matching policy sections
  And clearly indicates "This is a basic search result, not a full answer. Our AI assistant is temporarily unavailable."

Scenario: LLM service recovers
  Given the LLM service was down and has recovered
  When the next employee query arrives
  Then the system resumes normal RAG-based answer generation
```

---

### US-016: Authenticate via Corporate SSO

**Priority:** High
**Related requirements:** NFR-007, NFR-010

**Story:**
> As an **employee or administrator**,
> I want to **authenticate via my corporate SSO credentials**,
> so that **I don't need a separate account and access is governed by existing
> enterprise identity management**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee authenticates via Teams
  Given the employee is signed into Microsoft Teams with their corporate account
  When they open the chatbot
  Then they are automatically authenticated via SSO
  And they see the personalized greeting

Scenario: Employee authenticates via web widget
  Given the employee navigates to the intranet chat widget
  When they are prompted to authenticate
  Then they authenticate via Microsoft Entra ID SSO
  And they are granted employee-level access

Scenario: Administrator access is role-based
  Given a user authenticated via SSO has the "PolicyAdmin" role
  When they access the admin console
  Then they can upload documents, trigger re-indexing, and view analytics

Scenario: Unauthorized user cannot access admin console
  Given a user authenticated via SSO does NOT have the "PolicyAdmin" role
  When they attempt to access the admin console
  Then they receive a 403 Forbidden response
```

**Dependencies:**
- Depends on: Microsoft Entra ID configuration with appropriate role assignments
