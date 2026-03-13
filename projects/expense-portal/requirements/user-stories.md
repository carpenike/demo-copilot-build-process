# User Stories: Employee Expense Management Portal

> **Version:** 1.0
> **Status:** Draft
> **Date:** 2026-03-13
> **Produced by:** Requirements Agent

---

## Story Index

| ID | Title | Priority | FR Coverage | Status |
|----|-------|----------|-------------|--------|
| US-001 | Submit a new expense report | High | FR-001, FR-002, FR-006 | Draft |
| US-002 | Attach receipt with OCR pre-fill | High | FR-003, FR-004 | Draft |
| US-003 | Policy validation at submission | High | FR-005, FR-014, FR-015 | Draft |
| US-004 | Duplicate submission detection | Medium | FR-007 | Draft |
| US-005 | Manager approves expense report | High | FR-008, FR-010 | Draft |
| US-006 | Finance secondary review | High | FR-009 | Draft |
| US-007 | Auto-escalation for stale approvals | Medium | FR-011 | Draft |
| US-008 | Reject and resubmit expense report | High | FR-012 | Draft |
| US-009 | Configure expense policy rules | High | FR-013, FR-024 | Draft |
| US-010 | Workday data synchronization | High | FR-016 | Draft |
| US-011 | SAP payment batch generation | High | FR-017, FR-018 | Draft |
| US-012 | Finance reporting dashboard | High | FR-019, FR-021 | Draft |
| US-013 | Manager team spend dashboard | High | FR-020, FR-021 | Draft |
| US-014 | Approval and submission notifications | High | FR-022, FR-023 | Draft |

---

## Stories

---

### US-001: Submit a New Expense Report

**Priority:** High
**Related requirements:** FR-001, FR-002, FR-006

**Story:**
> As an **employee**,
> I want to **create and submit an expense report with line items detailing my business expenses**,
> so that **I can request reimbursement without using paper forms or email**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee creates a new expense report
  Given an authenticated employee on the expense portal
  When they create a new expense report with a title, date range, and business purpose
  And add at least one line item with date, category, vendor, amount, currency, and description
  Then the system saves the expense report
  And the report is submitted for approval

Scenario: Employee saves a draft expense report
  Given an authenticated employee with a partially completed expense report
  When they choose to save the report as a draft
  Then the system saves the current state of the report
  And the employee can return to the draft later to complete and submit it

Scenario: Employee submits report with missing required fields
  Given an authenticated employee creating a new expense report
  When they attempt to submit without filling in a required field (e.g., business purpose)
  Then the system prevents submission
  And displays a validation message indicating which fields are required

Scenario: Unauthenticated user attempts to create a report
  Given a user who is not authenticated via Microsoft Entra ID SSO
  When they attempt to access the expense submission page
  Then they are redirected to the SSO login page
```

**Out of scope for this story:**
- Receipt attachment and OCR (covered by US-002)
- Policy validation (covered by US-003)

**Dependencies:**
- Depends on: Workday sync (US-010) for employee identity and cost center data

---

### US-002: Attach Receipt with OCR Pre-Fill

**Priority:** High
**Related requirements:** FR-003, FR-004

**Story:**
> As an **employee**,
> I want to **upload a receipt image and have the system automatically extract key fields**,
> so that **I spend less time manually entering expense details and reduce data entry errors**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee uploads a valid receipt image
  Given an employee adding a line item to an expense report
  When they upload a receipt image in JPEG, PNG, or PDF format under 10 MB
  Then the system accepts the upload
  And applies OCR to extract amount, vendor, and date
  And pre-populates those fields where extraction confidence exceeds 85%

Scenario: Employee uploads a file exceeding the size limit
  Given an employee adding a line item to an expense report
  When they upload a receipt file larger than 10 MB
  Then the system rejects the upload
  And displays a message indicating the 10 MB file size limit

Scenario: Employee uploads an unsupported file type
  Given an employee adding a line item to an expense report
  When they upload a file that is not JPEG, PNG, or PDF
  Then the system rejects the upload
  And displays a message listing the accepted file formats

Scenario: OCR extraction has low confidence
  Given an employee uploads a receipt image
  When the OCR extraction confidence for a field is below 85%
  Then the system does not pre-populate that field
  And the employee must enter the value manually
```

**Out of scope for this story:**
- Multi-page PDF receipt splitting
- Receipt image enhancement or rotation

**Dependencies:**
- Depends on: US-001 (expense report creation)

---

### US-003: Policy Validation at Submission

**Priority:** High
**Related requirements:** FR-005, FR-014, FR-015

**Story:**
> As an **employee**,
> I want to **see specific policy violations on my expense line items before I submit**,
> so that **I can correct issues upfront and avoid rejections**.

**Acceptance Criteria:**

```gherkin
Scenario: Line item passes policy validation
  Given an employee has entered a line item within per diem limits and in a reimbursable category
  When they submit the expense report
  Then the system allows submission with no policy warnings

Scenario: Line item exceeds per diem rate
  Given an employee has entered a line item where the amount exceeds the per diem rate for the selected category and destination
  When the system validates the line item
  Then the system flags the line item with a specific message indicating the per diem limit exceeded
  And the employee must acknowledge the violation before submission

Scenario: Line item is in a non-reimbursable category
  Given an employee has entered a line item in a category marked as non-reimbursable
  When the system validates the line item
  Then the system blocks submission of that line item
  And displays a message indicating the category is not reimbursable

Scenario: Multiple policy violations on one report
  Given an expense report with multiple line items, some violating policy
  When the employee attempts to submit
  Then the system displays all violations inline next to the relevant line items
  And submission is blocked until violations are resolved or acknowledged
```

**Out of scope for this story:**
- Policy rule configuration (covered by US-009)

**Dependencies:**
- Depends on: US-009 (policy rules must be configured)

---

### US-004: Duplicate Submission Detection

**Priority:** Medium
**Related requirements:** FR-007

**Story:**
> As an **employee**,
> I want to **be warned if I am submitting a duplicate expense**,
> so that **I avoid accidental double reimbursement**.

**Acceptance Criteria:**

```gherkin
Scenario: System detects a potential duplicate
  Given an employee submits a line item with the same date, amount, and vendor as a previously submitted line item
  When the system checks for duplicates
  Then it displays a warning identifying the potential duplicate
  And the employee may choose to proceed or cancel

Scenario: No duplicate detected
  Given an employee submits a line item that does not match any prior submissions
  When the system checks for duplicates
  Then no warning is shown
  And submission proceeds normally
```

**Out of scope for this story:**
- Cross-employee duplicate detection (only same-employee duplicates)

**Dependencies:**
- Depends on: US-001 (expense report creation)

---

### US-005: Manager Approves Expense Report

**Priority:** High
**Related requirements:** FR-008, FR-010

**Story:**
> As a **cost center manager**,
> I want to **review and approve or reject my direct reports' expense submissions**,
> so that **I can control team spending and ensure policy compliance**.

**Acceptance Criteria:**

```gherkin
Scenario: Manager approves an expense report via web
  Given a manager with a pending expense report from a direct report
  When they review the report details and receipt images on the web portal
  And they approve the report
  Then the report status changes to "Manager Approved"
  And the employee receives an approval notification

Scenario: Manager approves via email action link
  Given a manager receives an email notification with an action link for a pending expense report
  When they click the approve action link
  Then the system authenticates the action via a single-use, time-bounded token
  And the report status changes to "Manager Approved"

Scenario: Manager requests more information
  Given a manager reviewing a pending expense report
  When they select "Request More Information" and provide a comment
  Then the employee receives a notification with the comment and a link to the report
  And the report status changes to "Information Requested"

Scenario: Manager attempts to approve their own expense
  Given a manager who has submitted their own expense report
  When the system routes the report for approval
  Then the report is routed to the manager's own manager (not to themselves)
  And segregation of duties is enforced

Scenario: Non-manager attempts to approve a report
  Given a user who is not the designated approver for a report
  When they attempt to approve it
  Then the system denies the action with a permission error
```

**Out of scope for this story:**
- Partial approval of individual line items (pending open question #3)
- Finance secondary review (covered by US-006)

**Dependencies:**
- Depends on: US-010 (Workday sync for manager hierarchy)

---

### US-006: Finance Secondary Review

**Priority:** High
**Related requirements:** FR-009

**Story:**
> As a **Finance team member**,
> I want to **review expense reports with high-value line items after manager approval**,
> so that **large expenditures receive appropriate financial oversight**.

**Acceptance Criteria:**

```gherkin
Scenario: Report with line item over $500 is escalated to Finance
  Given a manager has approved an expense report
  And the report contains at least one line item exceeding $500
  When the manager approval is recorded
  Then the system routes the report to the Finance review queue

Scenario: Report with no line items over $500 bypasses Finance review
  Given a manager has approved an expense report
  And all line items are $500 or under
  When the manager approval is recorded
  Then the report proceeds directly to final approved status
  And payment processing is initiated

Scenario: Finance approves the report
  Given a Finance reviewer with a report in the Finance review queue
  When they approve the report
  Then the report status changes to "Finance Approved"
  And payment processing is initiated

Scenario: Finance rejects the report
  Given a Finance reviewer with a report in the Finance review queue
  When they reject the report with a reason
  Then the employee receives a notification with the rejection reason
  And the report status changes to "Rejected"
```

**Dependencies:**
- Depends on: US-005 (manager approval)
- Blocks: US-011 (SAP payment batch generation)

---

### US-007: Auto-Escalation for Stale Approvals

**Priority:** Medium
**Related requirements:** FR-011

**Story:**
> As an **employee**,
> I want **my expense report to be automatically escalated if my manager hasn't acted within 5 business days**,
> so that **my reimbursement is not indefinitely delayed by an unresponsive approver**.

**Acceptance Criteria:**

```gherkin
Scenario: Report is escalated after 5 business days with no action
  Given an expense report has been pending manager approval for 5 business days
  And the manager has not approved, rejected, or requested more information
  When the escalation check runs
  Then the system routes the report to the approver's manager
  And the original approver and the employee are notified of the escalation

Scenario: Manager acts before the escalation deadline
  Given an expense report has been pending manager approval for 3 business days
  When the manager approves the report
  Then no escalation occurs

Scenario: Weekend and holidays are excluded from business day count
  Given an expense report submitted on a Friday
  When the system calculates the 5 business day deadline
  Then Saturday and Sunday are excluded from the count
```

**Out of scope for this story:**
- Configurable escalation time period (fixed at 5 business days for v1)

**Dependencies:**
- Depends on: US-005 (manager approval workflow)

---

### US-008: Reject and Resubmit Expense Report

**Priority:** High
**Related requirements:** FR-012

**Story:**
> As an **employee**,
> I want to **receive clear rejection feedback and be able to edit and resubmit my expense report**,
> so that **I can correct issues without starting over from scratch**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee resubmits a rejected report
  Given an employee whose expense report was rejected with a reason
  When they click the link in the rejection notification
  Then the system opens the rejected report in editable mode
  And the rejection reason is displayed at the top

Scenario: Resubmitted report enters approval workflow again
  Given an employee has edited a previously rejected expense report
  When they resubmit the report
  Then the report re-enters the approval workflow from the beginning (manager approval)
  And the report status changes to "Resubmitted"

Scenario: Rejected report retains original data
  Given an expense report that was rejected
  When the employee opens it for editing
  Then all original line items, receipts, and data are preserved
  And the employee can modify, add, or remove line items before resubmission
```

**Dependencies:**
- Depends on: US-005 (approval workflow)

---

### US-009: Configure Expense Policy Rules

**Priority:** High
**Related requirements:** FR-013, FR-024

**Story:**
> As a **Finance administrator**,
> I want to **configure per-category daily limits, non-reimbursable categories, and approval thresholds through an admin panel**,
> so that **I can update expense policies without requiring code changes or engineering involvement**.

**Acceptance Criteria:**

```gherkin
Scenario: Admin sets a per-category daily limit
  Given a Finance administrator on the admin panel
  When they set a daily limit for the "Meals" category to $75
  Then the policy engine enforces the $75 limit on all new submissions in the "Meals" category

Scenario: Admin adds a non-reimbursable category
  Given a Finance administrator on the admin panel
  When they mark "Personal Entertainment" as non-reimbursable
  Then employees cannot submit line items in that category

Scenario: Admin updates the Finance review threshold
  Given a Finance administrator on the admin panel
  When they change the Finance review threshold from $500 to $750
  Then reports with line items over $750 are escalated to Finance
  And reports with line items between $500 and $750 bypass Finance review

Scenario: Non-admin user attempts to access the admin panel
  Given a user without the Finance Administrator role
  When they attempt to access the admin panel
  Then the system denies access with a 403 Forbidden response
```

**Out of scope for this story:**
- Bulk import of policy rules from spreadsheet

**Dependencies:**
- Blocks: US-003 (policy validation depends on configured rules)

---

### US-010: Workday Data Synchronization

**Priority:** High
**Related requirements:** FR-016

**Story:**
> As the **system**,
> I want to **synchronize employee, manager hierarchy, and cost center data from Workday nightly**,
> so that **approval routing and cost center assignments are always based on current HR data**.

**Acceptance Criteria:**

```gherkin
Scenario: Nightly sync successfully updates employee data
  Given the Workday API is available
  When the nightly sync job runs
  Then the system updates employee records, manager assignments, and cost center mappings
  And a sync completion log is recorded with the number of records updated

Scenario: Nightly sync encounters Workday API unavailability
  Given the Workday API is unavailable during the sync window
  When the sync job runs
  Then the system retries the sync up to 3 times with exponential backoff
  And if all retries fail, an alert is sent to the operations team
  And the previous day's data remains in effect

Scenario: New employee added in Workday
  Given a new employee was added in Workday since the last sync
  When the nightly sync runs
  Then the new employee appears in the expense portal and can submit reports on the next business day

Scenario: Manager reassignment in Workday
  Given an employee's manager was changed in Workday
  When the nightly sync runs
  Then new expense submissions are routed to the updated manager
  And reports already pending approval remain with the original approver
```

**Out of scope for this story:**
- Real-time Workday sync (pending open question #4)

**Dependencies:**
- Blocks: US-001, US-005 (employee data and manager hierarchy needed)

---

### US-011: SAP Payment Batch Generation

**Priority:** High
**Related requirements:** FR-017, FR-018

**Story:**
> As a **Finance team member**,
> I want **approved expense reports to automatically generate SAP IDoc payment batches and GL journal entries**,
> so that **reimbursements are processed without manual ERP data entry**.

**Acceptance Criteria:**

```gherkin
Scenario: Approved report generates SAP payment batch
  Given an expense report has received final approval (Finance approved or manager approved with no Finance review required)
  When the payment batch job runs
  Then the system generates an IDoc-format payment batch file
  And transmits it to the SAP S/4HANA interface
  And the report status changes to "Payment Processing"

Scenario: GL journal entry is created on approval
  Given an expense report has received final approval
  When the system processes the approval
  Then a GL journal entry record is written to SAP
  And the entry is coded to the employee's cost center and appropriate GL account

Scenario: SAP interface is unavailable
  Given the SAP S/4HANA interface is unavailable
  When the system attempts to transmit the payment batch
  Then the system queues the batch for retry
  And an alert is sent to the operations team
  And the report status changes to "Payment Pending"

Scenario: Batch processing performance
  Given a payment batch containing up to 1,000 line items
  When the batch generation job runs
  Then the batch is generated within 60 seconds
```

**Dependencies:**
- Depends on: US-006 (Finance approval)

---

### US-012: Finance Reporting Dashboard

**Priority:** High
**Related requirements:** FR-019, FR-021

**Story:**
> As a **Finance team member**,
> I want to **view a dashboard showing expense totals by period, cost center, category, and approval status**,
> so that **I have real-time visibility into organizational spend for reconciliation and budgeting**.

**Acceptance Criteria:**

```gherkin
Scenario: Finance views expense summary by period
  Given a Finance user on the reporting dashboard
  When they select a date range
  Then the dashboard displays total expenses grouped by period
  And the totals reflect the most recent data

Scenario: Finance filters by cost center
  Given a Finance user on the reporting dashboard
  When they filter by a specific cost center
  Then the dashboard shows only expenses charged to that cost center

Scenario: Finance exports report to CSV
  Given a Finance user viewing a filtered report
  When they click "Export to CSV"
  Then the system downloads a CSV file containing the currently displayed data
  And the CSV includes all columns visible in the report

Scenario: Finance user sees data across all cost centers
  Given a Finance user on the reporting dashboard
  When they view the default (unfiltered) dashboard
  Then they see expense data across all cost centers in the organization
```

**Out of scope for this story:**
- Interactive drill-down into individual expense reports from the dashboard

**Dependencies:**
- None (reads from existing approved report data)

---

### US-013: Manager Team Spend Dashboard

**Priority:** High
**Related requirements:** FR-020, FR-021

**Story:**
> As a **cost center manager**,
> I want to **see my team's submitted and approved expenses compared to the cost center budget**,
> so that **I can track spend and make informed decisions before the budget is exhausted**.

**Acceptance Criteria:**

```gherkin
Scenario: Manager views team spend vs. budget
  Given a manager on the manager dashboard
  When the dashboard loads
  Then it displays total submitted and approved expenses for the current period
  And shows the remaining budget for their cost center

Scenario: Manager can only see their own team's data
  Given a manager on the manager dashboard
  When they view expense data
  Then only expenses from their direct reports are displayed
  And they cannot access other teams' data

Scenario: Manager exports team spend report
  Given a manager viewing the team spend dashboard
  When they click "Export to CSV"
  Then the system downloads a CSV file with the displayed data

Scenario: Manager with no pending approvals
  Given a manager whose direct reports have no submitted expenses in the current period
  When the dashboard loads
  Then it displays zero spend and the full available budget
```

**Dependencies:**
- Depends on: US-010 (Workday sync for manager-to-employee mapping)

---

### US-014: Approval and Submission Notifications

**Priority:** High
**Related requirements:** FR-022, FR-023

**Story:**
> As an **employee or manager**,
> I want to **receive timely email and in-app notifications about expense report status changes**,
> so that **I can take required actions promptly and stay informed about my reimbursements**.

**Acceptance Criteria:**

```gherkin
Scenario: Employee receives submission confirmation
  Given an employee submits an expense report
  When the submission is recorded
  Then the employee receives an email notification and an in-app notification confirming submission

Scenario: Employee receives approval notification
  Given an expense report is approved (by manager or Finance)
  When the approval is recorded
  Then the employee receives a notification indicating the report was approved

Scenario: Employee receives rejection notification
  Given an expense report is rejected
  When the rejection is recorded
  Then the employee receives a notification with the rejection reason
  And the notification includes a link to edit and resubmit

Scenario: Manager receives pending approval notification
  Given an employee submits an expense report
  When the report is routed to their manager
  Then the manager receives an email notification with a summary and action links

Scenario: Approver receives reminder for stale report
  Given a report has been pending approval for 3 or more business days
  When the reminder check runs
  Then the approver receives a reminder notification to take action
```

**Dependencies:**
- Depends on: US-001, US-005 (submission and approval workflows)
