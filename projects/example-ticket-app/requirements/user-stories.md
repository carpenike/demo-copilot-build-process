# User Stories: Support Ticket Portal

> **Version:** 1.0
> **Status:** Approved
> **Date:** 2026-03-13
> **Produced by:** Requirements Agent

---

## Story Index

| ID | Title | Priority | FR Coverage | Status |
|----|-------|----------|-------------|--------|
| US-001 | Customer submits a ticket | High | FR-001, FR-002, FR-003 | Approved |
| US-002 | Customer tracks ticket status | High | FR-004, FR-005 | Approved |
| US-003 | Agent manages ticket queue | High | FR-006, FR-007, FR-008 | Approved |
| US-004 | Agent adds internal notes | Medium | FR-009 | Approved |
| US-005 | Agent searches and exports tickets | Medium | FR-010, FR-011 | Approved |
| US-006 | Email notifications on status change | High | FR-012, FR-013 | Approved |
| US-007 | Leadership views reporting dashboard | Medium | FR-014, FR-015, FR-016 | Approved |

---

## Stories

---

### US-001: Customer Submits a Support Ticket

**Priority:** High
**Related requirements:** FR-001, FR-002, FR-003

**Story:**
> As a **customer**,
> I want to **submit a support ticket with a description and attachments**,
> so that **the support team can investigate and resolve my issue**.

**Acceptance Criteria:**

```gherkin
Scenario: Successful ticket submission
  Given I am authenticated as a customer
  When I submit a ticket with subject "Login broken", description, and priority "High"
  Then the system creates the ticket and returns a unique ticket ID
  And I see a confirmation page with my ticket ID

Scenario: Attach files to a ticket
  Given I am creating a new ticket
  When I attach a 5MB PNG screenshot
  Then the attachment is accepted and linked to the ticket

Scenario: Attachment exceeds size limit
  Given I am creating a new ticket
  When I attach a 15MB file
  Then the system rejects the attachment with a clear error message
  And the rest of the ticket form is preserved

Scenario: Unauthenticated submission attempt
  Given I am not logged in
  When I attempt to access the ticket submission form
  Then I am redirected to the login page
```

**Dependencies:**
- Blocks: US-002, US-006

---

### US-002: Customer Tracks Ticket Status

**Priority:** High
**Related requirements:** FR-004, FR-005

**Story:**
> As a **customer**,
> I want to **view my submitted tickets and their current status**,
> so that **I know whether my issues are being worked on**.

**Acceptance Criteria:**

```gherkin
Scenario: View my tickets
  Given I am authenticated as a customer
  And I have 3 submitted tickets
  When I navigate to "My Tickets"
  Then I see all 3 tickets with their status, subject, and date

Scenario: Filter tickets by status
  Given I have tickets in Open, In Progress, and Resolved status
  When I filter by "Open"
  Then I see only my Open tickets

Scenario: Add a comment to an open ticket
  Given I have a ticket in "In Progress" status
  When I add a comment "Can you provide an update?"
  Then the comment appears on the ticket timeline
  And the assigned agent is notified

Scenario: Cannot see another customer's tickets
  Given another customer has ticket TKT-999
  When I attempt to access TKT-999
  Then I receive a 403 Forbidden response
```

**Dependencies:**
- Depends on: US-001

---

### US-003: Agent Manages Ticket Queue

**Priority:** High
**Related requirements:** FR-006, FR-007, FR-008

**Story:**
> As a **support agent**,
> I want to **view, assign, and update tickets in my queue**,
> so that **I can efficiently resolve customer issues**.

**Acceptance Criteria:**

```gherkin
Scenario: View unassigned tickets
  Given there are 10 unassigned tickets in the system
  When I view the "Unassigned" queue
  Then I see all 10 tickets sorted by priority (High first)

Scenario: Assign a ticket to myself
  Given there is an unassigned ticket TKT-042
  When I click "Assign to me" on TKT-042
  Then TKT-042 appears in my "Assigned to me" queue
  And it is removed from the unassigned queue

Scenario: Update ticket status
  Given I am assigned ticket TKT-042 in "Open" status
  When I change the status to "In Progress"
  Then the status is updated
  And the customer receives an email notification

Scenario: Invalid status transition
  Given ticket TKT-042 is in "Closed" status
  When I attempt to change status to "In Progress"
  Then the system rejects the transition with a validation error
```

---

### US-004: Agent Adds Internal Notes

**Priority:** Medium
**Related requirements:** FR-009

**Story:**
> As a **support agent**,
> I want to **add internal notes to a ticket that only agents can see**,
> so that **I can document investigation steps without exposing them to the customer**.

**Acceptance Criteria:**

```gherkin
Scenario: Add an internal note
  Given I am viewing ticket TKT-042
  When I add an internal note "Checked DB logs — user row exists, auth token expired"
  Then the note appears on the ticket timeline marked as "Internal"

Scenario: Customer cannot see internal notes
  Given ticket TKT-042 has 2 customer comments and 1 internal note
  When the customer views TKT-042
  Then they see only the 2 customer comments
  And the internal note is not present in the response
```

---

### US-005: Agent Searches and Exports Tickets

**Priority:** Medium
**Related requirements:** FR-010, FR-011

**Story:**
> As a **support agent**,
> I want to **search tickets by keyword and export results to CSV**,
> so that **I can find related issues and produce reports**.

**Acceptance Criteria:**

```gherkin
Scenario: Full-text search
  Given there are 500 tickets in the system
  When I search for "password reset"
  Then I receive tickets containing "password reset" in subject, description, or comments
  And results are returned within 500ms

Scenario: Export filtered results to CSV
  Given I have filtered tickets to "Resolved" status in March 2026
  When I click "Export to CSV"
  Then a CSV file downloads containing the filtered ticket data
  And it includes columns: ID, Subject, Status, Priority, Created, Resolved, Agent
```

---

### US-006: Email Notifications on Status Change

**Priority:** High
**Related requirements:** FR-012, FR-013

**Story:**
> As a **customer**,
> I want to **receive an email when my ticket status changes**,
> so that **I stay informed without checking the portal constantly**.

**Acceptance Criteria:**

```gherkin
Scenario: Notification on status change
  Given my ticket TKT-042 is in "Open" status
  When an agent changes it to "In Progress"
  Then I receive an email with subject "Ticket TKT-042 updated: In Progress"
  And the email body includes the new status

Scenario: Agent notified on customer comment
  Given I am the assigned agent on TKT-042
  When the customer adds a comment
  Then I receive an email notification with the comment text
```

---

### US-007: Leadership Views Reporting Dashboard

**Priority:** Medium
**Related requirements:** FR-014, FR-015, FR-016

**Story:**
> As a **support operations manager**,
> I want to **view a dashboard of ticket metrics and agent performance**,
> so that **I can identify trends and allocate resources effectively**.

**Acceptance Criteria:**

```gherkin
Scenario: View ticket volume dashboard
  Given there are tickets across multiple periods
  When I access the reporting dashboard
  Then I see total ticket volume, average resolution time, and breakdown by status

Scenario: View agent performance
  Given agents have resolved tickets this month
  When I view the "Agent Performance" section
  Then I see per-agent metrics: resolved count, avg resolution time, open count

Scenario: Dashboard data freshness
  Given a ticket was resolved 3 minutes ago
  When I refresh the dashboard
  Then the resolved ticket is reflected in the metrics (within 5-minute refresh window)
```
