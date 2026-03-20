---
name: verification-before-completion
description: "Use when about to claim work is complete, fixed, or passing — requires running verification commands and confirming output before making any success claims. Evidence before assertions, always."
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this response, you cannot claim it passes.

## The Gate Function

Before claiming any status or expressing satisfaction:

1. **IDENTIFY** — What command proves this claim?
2. **RUN** — Execute the FULL command (fresh, complete)
3. **READ** — Full output, check exit code, count failures
4. **VERIFY** — Does output confirm the claim?
   - If NO → State actual status with evidence
   - If YES → State claim WITH evidence
5. **ONLY THEN** — Make the claim

Skip any step = lying, not verifying.

## Verification Requirements by Claim

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Mypy passes | `mypy` output: exit 0 | Ruff passing |
| Coverage gate met | `--cov-fail-under=80`: exit 0 | "Tests pass" without coverage check |
| Dockerfile builds | `docker build`: exit 0 | Dockerfile exists |
| Requirements met | Line-by-line checklist verified | Tests passing |

## Pipeline-Specific Verification

### For @3-implementation
Before claiming the verification gate passes, you MUST run and cite output for:
```bash
uvx ruff check app/           # Must see: exit 0
uvx ruff format --check app/  # Must see: exit 0
mypy app/                     # Must see: exit 0
```

### For @4-test
Before claiming tests pass:
```bash
python -m pytest ../tests/ -x -q --cov=app --cov-fail-under=80
```
Cite the actual pass count and coverage percentage.

### For @7-review
Before marking any checklist item ✅, you must have run the relevant command
and cite the output. Do not mark items as passing based on prior agent claims.

## Red Flags — STOP

If you catch yourself thinking any of these, STOP and run verification:

- "Should work now"
- "Looks correct"
- "I'm confident this is right"
- "Just this once I can skip verification"
- "The linter passed, so mypy will too"
- "I made the same fix before and it worked"

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ type checker ≠ test suite |
| "Previous agent verified it" | Verify independently |
| "Partial check is enough" | Partial proves nothing about the whole |

## When to Apply

**ALWAYS before:**
- ANY claim of success or completion
- ANY expression of satisfaction ("Done!", "All good!", "Fixed!")
- Marking any verification gate item as ✅
- Committing code
- Printing a handoff summary
- Moving to the next pipeline stage

## The Bottom Line

Run the command. Read the output. THEN claim the result.

This is non-negotiable.
