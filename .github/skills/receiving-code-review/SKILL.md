---
name: receiving-code-review
description: "Use when @3-implementation or @4-test receives findings from @7-review or mid-pipeline review — provides structured guidance on prioritizing fixes, verifying each fix independently, and avoiding scope creep during remediation."
---

# Receiving Code Review

## Overview

When review findings come back — from @7-review, from a mid-pipeline review,
or from a human reviewer — handle them systematically. Fix critical issues
first, verify each fix independently, and resist the urge to refactor during
remediation.

**Core principle:** Fix what was found. Verify the fix. Don't touch anything else.

## When to Use

- @7-review produces a FAIL report with findings routed to your agent
- A mid-pipeline review (via requesting-code-review skill) flags issues
- A human reviewer comments on code in a PR
- Any time you receive structured feedback with findings to address

## The Process

### 1. Read All Findings First

Don't start fixing after reading the first finding. Read the entire report to:
- Understand the full scope of issues
- Identify dependencies between findings (e.g., FAIL-001 may resolve FAIL-003)
- Spot patterns (multiple findings from the same root cause)

### 2. Prioritize by Severity

Fix in this order — no exceptions:

| Priority | Severity | Action |
|----------|----------|--------|
| 1 | **Critical** | Fix immediately. These block the pipeline. |
| 2 | **High** | Fix before committing. These will cascade to downstream stages. |
| 3 | **Medium** | Fix if straightforward. Flag for follow-up if complex. |
| 4 | **Low / Info** | Note for future. Don't fix during this remediation pass. |

### 3. Fix One Finding at a Time

For each finding:

1. **Read the finding** — understand what was found and what standard it violates
2. **Read the remediation** — the reviewer may have specified what to do
3. **Make the minimal fix** — don't refactor, don't improve, don't clean up
4. **Verify the fix** — run the relevant verification command
5. **Move to the next finding**

### 4. Don't Fix During Remediation

These are NOT permitted during a fix pass:

| Temptation | Why Not |
|------------|---------|
| "While I'm here, let me also refactor..." | Refactoring introduces new bugs. Fix only what was found. |
| "This code could be cleaner..." | Agreed, but not now. File an issue. |
| "I should add more tests..." | Only add tests if a finding specifically requires it. |
| "Let me update the docs too..." | Only if a finding says docs are wrong. |

### 5. Verify All Fixes Together

After fixing all findings, run the full verification suite:

```bash
uvx ruff check app/           # Must pass
uvx ruff format --check app/  # Must pass
mypy app/                     # Must pass
python -m pytest ../tests/ -x -q --cov=app --cov-fail-under=80  # Must pass
```

If any command fails, follow the **systematic-debugging** skill.

### 6. Handling Disagreements

If you believe a finding is incorrect:

- **Don't silently skip it** — that's dishonesty
- **Document your reasoning** — explain why you believe the finding is wrong
- **Reference evidence** — cite the ADR, standard, or requirement that supports your position
- **Let the reviewer decide** — present your case, accept the outcome

## Integration with Pipeline

- **@3-implementation** uses this when @7-review routes findings back
- **@4-test** uses this when test-related findings are routed back
- Pairs with **verification-before-completion** — verify each fix with evidence
- Pairs with **systematic-debugging** — when a fix introduces new failures
