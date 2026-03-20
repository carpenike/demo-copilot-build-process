# User Stories: Policy Chatbot

> **Version:** 1.0
> **Status:** Draft
> **Date:** 2026-03-20
> **Produced by:** Requirements Agent

---

## Story Index

| ID | Title | Priority | FR Coverage | Status |
|----|-------|----------|-------------|--------|
| US-001 | Ask a Policy Question | High | FR-007, FR-008, FR-012, FR-013, FR-014, FR-015 | Draft |
| US-002 | Follow-Up Conversation | High | FR-009 | Draft |
| US-003 | Get a Next-Step Checklist | High | FR-017, FR-018, FR-019, FR-020, FR-021 | Draft |
| US-004 | Wayfinding Assistance | Medium | FR-022, FR-023, FR-024 | Draft |
| US-005 | Escalate to Live Agent | High | FR-025, FR-026, FR-027 | Draft |
| US-006 | Confidential Topic Handling | High | FR-016 | Draft |
| US-007 | Provide Feedback on a Response | Medium | FR-028, FR-030 | Draft |
| US-008 | Upload and Index a Policy Document | High | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-031 | Draft |
| US-009 | Test Query Preview | Medium | FR-032 | Draft |
| US-010 | View Analytics Dashboard | Medium | FR-029, FR-030 | Draft |
| US-011 | Personalized Greeting and Role-Aware Response | Low | FR-011 | Draft |
| US-012 | Policy Coverage Report | Low | FR-033 | Draft |

---

## Stories

---

### US-001: Ask a Policy Question

**Priority:** High
**Related requirements:** FR-007, FR-008, FR-012, FR-013, FR-014, FR-015

**Story:**
> As an **employee**,
> I want to **ask a natural language question about corporate policy**,
> so that **I get an accurate, cited answer in under 2 minutes instead of
> searching through multiple document repositories**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee asks a question with a matching policy
  Given the employee is authenticated via SSO
  And the employee opens the chat widget on the intranet or in Microsoft Teams
  When the employee types "What is the bereavement leave policy?"
  Then the system returns a natural language answer grounded in indexed policy content
  And the response includes a citation block with policy title, section, effective date, and source link
  And the response includes the standard legal disclaimer
  And the response is returned within 5 seconds

Scenario: Employee asks a question with no matching policy
  Given the employee is authenticated via SSO
  When the employee types a question that does not match any indexed policy
  Then the system responds indicating no matching policy was found
  And the system offers to connect the employee to the appropriate support team
  And the system does not generate an answer from general knowledge

Scenario: Employee asks a factual question vs. a procedural question
  Given the employee is authenticated via SSO
  When the employee types "Who approves expense reports over $5,000?"
  Then the system classifies the intent as factual (what/who/when)
  And the system returns the relevant policy answer with citation
```

**Out of scope for this story:**
- Follow-up questions within the same conversation (see US-002)
- Procedural checklists (see US-003)

**Dependencies:**
- Depends on: FR-001 through FR-006 (document ingestion must be complete)

---

### US-002: Follow-Up Conversation

**Priority:** High
**Related requirements:** FR-009

**Story:**
> As an **employee**,
> I want to **ask follow-up questions that reference my previous question**,
> so that **I can drill into policy details without repeating myself**.

**Acceptance Criteria:**

```gherkin
Scenario: Follow-up question uses prior conversation context
  Given the employee previously asked "What is the PTO policy?"
  And the system returned an answer about PTO accrual and usage
  When the employee asks "What about for part-time employees?"
  Then the system resolves the follow-up against the prior PTO context
  And the system returns PTO policy details specific to part-time employees
  And the response includes a citation to the relevant policy section

Scenario: Employee starts a new topic within the same session
  Given the employee previously asked about PTO policy
  When the employee asks "How do I request a parking badge?"
  Then the system recognizes this is a new topic unrelated to PTO
  And the system returns the relevant parking badge policy answer
```

**Out of scope for this story:**
- Cross-session memory (conversation context is per-session only)

**Dependencies:**
- Depends on: US-001

---

### US-003: Get a Next-Step Checklist

**Priority:** High
**Related requirements:** FR-017, FR-018, FR-019, FR-020, FR-021

**Story:**
> As an **employee**,
> I want to **receive a step-by-step checklist when I ask how to do something**,
> so that **I know exactly what actions I need to take and which ones the system
> can help me with**.

**Acceptance Criteria:**

```gherkin
Scenario: Procedural query generates a numbered checklist
  Given the employee is authenticated via SSO
  When the employee asks "How do I request FMLA leave?"
  Then the system returns a numbered checklist of all required steps
  And each step is classified as either "Assisted" or "Manual"
  And the checklist is derived from the indexed FMLA policy document

Scenario: Assisted checklist step offers actionable help
  Given the checklist includes a step to "Submit the FMLA request form in Workday"
  And this step is classified as "Assisted"
  Then the system provides a deep link to the Workday FMLA form
  And the link pre-populates fields where the API supports it

Scenario: Manual checklist step clearly states the required action
  Given the checklist includes a step to "Obtain a medical certification from your healthcare provider"
  And this step is classified as "Manual"
  Then the system clearly states "Call your healthcare provider to request a medical certification"
  And the system does not imply it can perform or automate this step

Scenario: Employee asks for more detail on a checklist step
  Given the system has returned a checklist with 5 steps
  When the employee asks "Tell me more about step 3"
  Then the system provides expanded detail for that specific step
  And the additional detail is grounded in the source policy document
```

**Out of scope for this story:**
- Wayfinding-specific assistance (see US-004)
- Tracking checklist completion state across sessions

**Dependencies:**
- Depends on: US-001

---

### US-004: Wayfinding Assistance

**Priority:** Medium
**Related requirements:** FR-022, FR-023, FR-024

**Story:**
> As an **employee**,
> I want to **get directions to a physical location when a policy step requires
> visiting an office or facility**,
> so that **I can find the right place without asking around**.

**Acceptance Criteria:**

```gherkin
Scenario: Wayfinding data is available for the employee's campus
  Given the employee is located at HQ campus
  And wayfinding data is available for HQ
  When a checklist step requires visiting "Room 204, Building C"
  Then the system provides a link to the campus map with Building C, Room 204 pre-selected
  And the system displays navigation directions to the destination

Scenario: Wayfinding data is not available for the employee's campus
  Given the employee is located at a satellite office
  And no wayfinding data is available for that campus
  When a checklist step requires visiting "the Security desk"
  Then the system falls back to displaying the building name, room number, and floor
  And the system does not display a broken map link

Scenario: Standalone wayfinding question
  Given the employee is authenticated via SSO
  When the employee asks "Where is the HR office on East Campus?"
  Then the system provides the building, floor, and room number
  And if wayfinding data is available, includes a campus map link
```

**Out of scope for this story:**
- Indoor turn-by-turn navigation
- Real-time availability of office staff

**Dependencies:**
- Depends on: Facilities team providing campus map data and wayfinding API access (Assumption #3)

---

### US-005: Escalate to Live Agent

**Priority:** High
**Related requirements:** FR-025, FR-026, FR-027

**Story:**
> As an **employee**,
> I want to **be transferred to a live service desk agent at any time**,
> so that **I can get human help when the chatbot cannot resolve my question**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee explicitly requests a live agent
  Given the employee is in an active chat session
  When the employee types "talk to a person"
  Then the system initiates a handoff to a live service desk agent
  And the system passes the conversation transcript and identified intent to the agent via the ticketing system API
  And the employee does not have to repeat their question

Scenario: Employee uses alternative phrasing to request escalation
  Given the employee is in an active chat session
  When the employee types "I need to speak with someone" or "connect me to HR"
  Then the system recognizes the escalation intent
  And the system initiates the same handoff process

Scenario: Automatic escalation after repeated low-confidence answers
  Given the system has failed to provide a relevant answer on two consecutive attempts
  And the answer confidence is below the configured threshold
  Then the system automatically offers escalation to a live agent
  And the system informs the employee: "I'm having trouble finding the right answer. Let me connect you with someone who can help."

Scenario: Conversation context is preserved during escalation
  Given the employee asked 3 questions before requesting escalation
  When the handoff to the live agent occurs
  Then the service desk agent receives the full conversation transcript
  And the agent receives the system's identified intent and policy domain
```

**Out of scope for this story:**
- Live agent queue management or routing logic (owned by ServiceNow)
- Video or voice escalation

**Dependencies:**
- Depends on: ServiceNow REST API for conversation handoff (Assumption #4)

---

### US-006: Confidential Topic Handling

**Priority:** High
**Related requirements:** FR-016

**Story:**
> As an **employee**,
> I want the chatbot to **recognize when my question involves a confidential HR
> matter and immediately offer human support**,
> so that **sensitive topics are handled appropriately and privately**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee asks about harassment policy
  Given the employee is authenticated via SSO
  When the employee types "I want to report harassment"
  Then the system detects this as a confidential HR matter
  And the system does not generate a chatbot answer about the topic
  And the system immediately offers direct escalation to HR
  And the system displays contact information for confidential HR support

Scenario: Employee asks about whistleblower or discrimination
  Given the employee is authenticated via SSO
  When the employee types "How do I file a discrimination complaint?"
  Then the system detects this as a confidential HR matter
  And the system offers direct escalation without providing a policy-generated answer

Scenario: Employee asks a general question about a sensitive policy area
  Given the employee types "What is the company's anti-harassment training schedule?"
  Then the system recognizes this as a factual/informational question (not a report)
  And the system provides the training schedule information with citation
  And the system does not trigger the confidential topic escalation
```

**Out of scope for this story:**
- Case management or investigation tracking
- Anonymous reporting (in-scope system requires SSO authentication)

**Dependencies:**
- Depends on: HR team providing the list of topics classified as confidential

---

### US-007: Provide Feedback on a Response

**Priority:** Medium
**Related requirements:** FR-028, FR-030

**Story:**
> As an **employee**,
> I want to **rate chatbot responses and optionally leave a comment**,
> so that **the system can be improved based on real user experience**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee gives positive feedback
  Given the system has returned an answer to the employee's question
  When the employee clicks the thumbs-up button
  Then the system records the positive feedback associated with the query and response
  And the employee can optionally type a free-text comment

Scenario: Employee gives negative feedback with a comment
  Given the system has returned an answer to the employee's question
  When the employee clicks the thumbs-down button
  And the employee types "This answer is outdated"
  Then the system records the negative feedback with the comment
  And the query is counted toward the negative-feedback threshold for that topic

Scenario: Topic flagged after repeated negative feedback
  Given a topic has received negative feedback more than 3 times
  Then the system flags the topic for admin review
  And the flagged topic appears in the admin analytics dashboard

Scenario: Employee skips feedback
  Given the system has returned an answer
  When the employee asks a new question without providing feedback
  Then the system proceeds normally without requiring feedback
```

**Out of scope for this story:**
- Admin response to flagged feedback (see US-010)

**Dependencies:**
- None

---

### US-008: Upload and Index a Policy Document

**Priority:** High
**Related requirements:** FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-031

**Story:**
> As a **policy administrator**,
> I want to **upload a new or updated policy document and trigger re-indexing**,
> so that **the chatbot answers reflect the latest approved policy content**.

**Acceptance Criteria:**

```gherkin
Scenario: Administrator uploads a new PDF policy document
  Given the administrator is authenticated with admin role
  When the administrator uploads a PDF file via the admin console
  And provides metadata: title, category, effective date, owner
  Then the system ingests the document and extracts text content preserving structure
  And the system indexes the document for semantic retrieval
  And the document appears in the policy inventory with "Active" status

Scenario: Administrator triggers re-indexing of an existing document
  Given a policy document is already indexed
  When the administrator uploads a revised version of the document
  And triggers re-indexing via the admin console
  Then the system re-indexes the document within 5 minutes (for documents up to 200 pages)
  And the previous version is retained in version history
  And the new version becomes the active version

Scenario: Administrator retires an outdated document
  Given a policy document is currently active in the corpus
  When the administrator marks the document as retired
  Then the document is removed from the active corpus
  And the chatbot no longer returns answers based on the retired document
  And the document remains in version history for audit purposes

Scenario: Full corpus re-indexing
  Given there are approximately 140 documents (~8,000 pages) in the corpus
  When the administrator triggers a full corpus re-index
  Then the re-indexing completes within 2 hours
  And the system remains available to answer queries during re-indexing (with potentially stale results)
```

**Out of scope for this story:**
- Automated detection of policy changes in source repositories (v2 feature)
- Policy authoring or editing within the admin console

**Dependencies:**
- Depends on: Document source systems being accessible (SharePoint, intranet CMS, blob storage)

---

### US-009: Test Query Preview

**Priority:** Medium
**Related requirements:** FR-032

**Story:**
> As a **policy administrator**,
> I want to **preview how the chatbot would answer a question before and after
> a document change**,
> so that **I can verify answer quality before the change goes live**.

**Acceptance Criteria:**

```gherkin
Scenario: Administrator tests a query against current corpus
  Given the administrator is authenticated with admin role
  When the administrator enters a test query in the admin console
  Then the system returns the answer the chatbot would produce
  And the answer includes the citation block and source documents used

Scenario: Administrator compares answers before and after a document update
  Given the administrator has uploaded a revised policy document (not yet published)
  When the administrator enters a test query in the admin console
  Then the system shows the current live answer and the preview answer side by side
  And the administrator can review differences before publishing the document

Scenario: Test query reveals a gap in coverage
  Given the administrator enters a test query
  When no relevant policy content is found
  Then the system returns the "no matching policy found" fallback response
  And the administrator can identify the coverage gap
```

**Out of scope for this story:**
- A/B testing of different prompt configurations
- Bulk test query execution

**Dependencies:**
- Depends on: US-008 (document upload and indexing)

---

### US-010: View Analytics Dashboard

**Priority:** Medium
**Related requirements:** FR-029, FR-030

**Story:**
> As a **policy administrator**,
> I want to **view usage analytics and identify trends in employee policy
> questions**,
> so that **I can measure chatbot effectiveness and improve content coverage**.

**Acceptance Criteria:**

```gherkin
Scenario: Administrator views query volume metrics
  Given the administrator is authenticated with admin role
  When the administrator opens the analytics dashboard
  Then the dashboard displays daily, weekly, and monthly query volume
  And the dashboard displays the top 20 intents by frequency

Scenario: Administrator reviews resolution and escalation rates
  Given the analytics dashboard is open
  When the administrator navigates to the resolution metrics
  Then the dashboard displays the resolution rate (queries answered without escalation)
  And the dashboard displays the escalation rate
  And the dashboard displays the average satisfaction score from feedback

Scenario: Administrator reviews unanswered query log
  Given the analytics dashboard is open
  When the administrator navigates to the unanswered queries section
  Then the system displays a log of queries that could not be matched to a policy
  And each entry shows the query text, timestamp, and any identified intent

Scenario: Administrator reviews flagged negative feedback topics
  Given certain topics have been flagged due to repeated negative feedback
  When the administrator navigates to the flagged topics section
  Then each flagged topic is listed with the count of negative ratings and sample comments
```

**Out of scope for this story:**
- Custom report generation or data export
- Real-time alerting on metrics thresholds

**Dependencies:**
- Depends on: US-007 (feedback collection)

---

### US-011: Personalized Greeting and Role-Aware Response

**Priority:** Low
**Related requirements:** FR-011

**Story:**
> As an **employee**,
> I want the chatbot to **greet me by name and tailor answers based on my role,
> department, and location when relevant**,
> so that **I receive policy guidance specific to my situation**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee is greeted by first name
  Given the employee is authenticated via SSO
  And the corporate directory contains the employee's first name
  When the employee opens the chat widget
  Then the system greets the employee by first name

Scenario: Policy varies by employee location
  Given the employee is located at "East Campus"
  And the parking policy has location-specific variations
  When the employee asks "How do I get a parking permit?"
  Then the system returns the parking policy answer tailored to East Campus
  And the citation references the location-specific section

Scenario: No role-specific variation exists
  Given the employee asks about a policy that applies uniformly
  When the system retrieves the policy content
  Then the system returns the standard policy answer without role-based variation
```

**Out of scope for this story:**
- Manager-only policy visibility (pending Open Question #6)
- Employee profile editing

**Dependencies:**
- Depends on: Microsoft Entra ID / Graph API providing employee name, department,
  location, and manager data (Assumption #6)

---

### US-012: Policy Coverage Report

**Priority:** Low
**Related requirements:** FR-033

**Story:**
> As a **policy administrator**,
> I want to **see which policy domains have indexed coverage and which have
> gaps**,
> so that **I can prioritize content loading and identify missing policies**.

**Acceptance Criteria:**

```gherkin
Scenario: Administrator views the policy coverage report
  Given the administrator is authenticated with admin role
  When the administrator opens the policy coverage report in the admin console
  Then the report lists all defined policy categories (HR, IT, Finance, Facilities, Legal, Compliance, Safety)
  And for each category, shows the count of indexed documents
  And highlights categories with zero indexed documents as "gaps"

Scenario: New document upload updates the coverage report
  Given the Facilities category shows 0 indexed documents
  When the administrator uploads a Facilities policy document and indexing completes
  Then the coverage report updates to show 1 indexed document in Facilities
  And the Facilities category is no longer highlighted as a gap
```

**Out of scope for this story:**
- Content quality scoring per document
- Automated recommendations for missing policies

**Dependencies:**
- Depends on: US-008 (document upload and indexing)
