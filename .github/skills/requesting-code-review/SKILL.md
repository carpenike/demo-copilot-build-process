---
name: requesting-code-review
description: "Use when completing a major implementation task or pipeline stage — dispatches a structured review to catch issues before they cascade to downstream agents. Review early, review often."
---

# Requesting Code Review

## Overview

Don't wait until @7-review to catch issues. Request focused reviews after
completing major implementation work so problems are caught early when they're
cheapest to fix.

**Core principle:** Review early, review often. Issues caught at @3 are cheaper
than issues caught at @7.

## When to Request Review

**Mandatory:**
- After @3-implementation completes all endpoints before handoff to @4-test
- After @4-test discovers issues that require implementation changes
- Before any commit when the changeset touches 5+ files

**Optional but valuable:**
- After implementing a complex algorithm or business rule
- When uncertain about a design interpretation
- After fixing a bug found by systematic-debugging

## How to Request Review

### 1. Summarize What Was Built

State concisely:
- What was implemented (endpoint, service, model)
- Which ADR or requirement it fulfills
- What design decisions were made during implementation

### 2. Identify Review Focus Areas

Direct the reviewer's attention:

```markdown
## Review Request: Expense API Implementation

**Implemented:** POST/GET/PUT endpoints for /v1/expenses
**Fulfills:** FR-001 through FR-005, ADR-0001 (Python/FastAPI)

**Focus areas:**
1. Does the approval workflow match the wireframe-spec state machine?
2. Is the policy engine validation complete per FR-003?
3. Are the Pydantic models strict enough for financial data?

**Known trade-offs:**
- Used synchronous DB calls for simplicity — async migration planned for Task 6
```

### 3. Review Against Plan

If a writing-plans implementation plan exists, review against it:
- Were all planned tasks completed?
- Did any tasks deviate from the plan? Why?
- Are there plan items that need revision?

### 4. Review Checklist

For @3-implementation reviews, check:

| Category | Check |
|----------|-------|
| **Spec compliance** | Does the code match the wireframe-spec contracts? |
| **ADR compliance** | Does the code use the technologies specified in ADRs? |
| **Enterprise standards** | No secrets, type hints, ruff/mypy clean? |
| **Test coverage** | Does every new function have a test (per TDD skill)? |
| **Error handling** | Are error paths handled, not swallowed? |
| **Security** | No CORS wildcards, no public endpoints without auth? |

## Acting on Review Feedback

### Critical Issues
Fix immediately. Do not proceed until resolved.

### Important Issues
Fix before committing. These will cascade to downstream agents.

### Suggestions
Note for later. Don't let perfect be the enemy of done.

### Disagreements
If you believe feedback is incorrect:
- Explain your reasoning with specific evidence
- Reference the ADR, requirement, or standard that supports your decision
- Don't dismiss feedback without explanation

## Integration with Pipeline

- **@3-implementation** requests review before handoff to @4-test
- **@4-test** can request review when tests reveal implementation issues
- **@7-review** performs the comprehensive final review — mid-pipeline reviews
  reduce the number of findings at that stage
- Reviews use the verification-before-completion skill — cite evidence, not claims
