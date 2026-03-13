# User Stories: [Project Name]

> **Version:** 1.0
> **Status:** [Draft | In Review | Approved]
> **Date:** YYYY-MM-DD
> **Produced by:** Requirements Agent

---

## Story Index

| ID | Title | Priority | FR Coverage | Status |
|----|-------|----------|-------------|--------|
| US-001 | [Title] | High | FR-001, FR-002 | Draft |
| US-002 | [Title] | Medium | FR-003 | Draft |

---

## Stories

---

### US-001: [Short Descriptive Title]

**Priority:** High / Medium / Low
**Related requirements:** FR-001, FR-002

**Story:**
> As a **[persona]**,
> I want to **[action/capability]**,
> so that **[business outcome/value]**.

**Acceptance Criteria:**

```gherkin
Scenario: [Happy path scenario name]
  Given [the starting context / preconditions]
  When [the user takes an action]
  Then [the expected outcome occurs]
  And [any additional assertions]

Scenario: [Edge case or failure scenario]
  Given [context where something could go wrong]
  When [the action is taken]
  Then [the system handles it gracefully]
  And [the user sees an appropriate message]

Scenario: [Permission/auth scenario if applicable]
  Given [a user without the required permission]
  When [they attempt the action]
  Then [they receive a 403 / permission denied response]
```

**Out of scope for this story:**
- [What this story intentionally does NOT cover]

**Dependencies:**
- Depends on: [US-XXX or FR-XXX]
- Blocks: [US-XXX]

---

### US-002: [Short Descriptive Title]

[Repeat structure above]
