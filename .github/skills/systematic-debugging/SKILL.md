---
name: systematic-debugging
description: "Use when encountering any bug, test failure, lint error, build failure, or unexpected behavior — before proposing fixes. Requires root cause investigation before attempting solutions."
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue encountered during the pipeline:
- Ruff lint errors
- Mypy type errors
- Test failures
- Build failures (Docker, uv, pip)
- Import errors or circular dependencies
- Unexpected behavior in generated code
- Integration test failures
- CI pipeline failures

**Use this ESPECIALLY when:**
- Under pressure to finish a pipeline stage
- "Just one quick fix" seems obvious
- You've already tried a fix and it didn't work
- A previous agent's output causes issues in your stage

## The Four Phases

### Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

1. **Read error messages carefully**
   - Don't skip past errors or warnings
   - Read stack traces completely
   - Note line numbers, file paths, error codes
   - Error messages often contain the exact solution

2. **Reproduce consistently**
   - Run the failing command again to confirm
   - Can you trigger it reliably?
   - Is it environment-specific (CI vs local)?

3. **Check recent changes**
   - What did you just change that could cause this?
   - Did a previous agent produce something unexpected?
   - Are there dependency conflicts?

4. **Trace data flow**
   - Where does the bad value originate?
   - What called this with the wrong arguments?
   - Keep tracing backward until you find the source

### Phase 2: Pattern Analysis

1. **Find working examples** — Look at similar working code in this codebase
2. **Compare** — What's different between working and broken?
3. **Identify differences** — List every difference, however small
4. **Understand dependencies** — What assumptions does the broken code make?

### Phase 3: Hypothesis and Testing

1. **Form a single hypothesis** — "I think X is the root cause because Y"
2. **Test minimally** — Make the SMALLEST change to test your hypothesis
3. **One variable at a time** — Don't fix multiple things at once
4. **Verify** — Did it work? If not, form a NEW hypothesis

### Phase 4: Implementation

1. **Fix the root cause** — Not the symptom
2. **One change at a time** — No bundled refactoring
3. **Verify the fix** — Run the full verification command
4. **Check for regressions** — Did other things break?

**If 3+ fixes fail:** STOP. The problem may be architectural. Surface it to
the user rather than continuing to thrash. If a previous agent produced a
design flaw, recommend routing back to that agent.

## Pipeline-Specific Debugging Patterns

### Ruff Errors
- Read the rule code (e.g., `S101`, `B008`) — understand what it flags
- Check if the rule is in the mandatory set before suppressing with `noqa`
- Don't blanket-suppress rules — fix the underlying issue

### Mypy Errors
- Trace the type mismatch to its source
- Don't add `type: ignore` without a specific error code
- Check if the type stub is installed (`types-*` packages)

### Test Failures
- Read the assertion error — what was expected vs actual?
- Is the mock set up correctly? (side_effect vs return_value)
- FastAPI returns 422 for validation errors, not 400
- Are environment variables set for Settings?

### Import Errors
- Module-scope code runs at import time — don't call config functions there
- Azure SDKs need lazy imports in CI environments
- Check circular import chains

### Docker Build Failures
- Check multi-stage build stage names
- Verify base image exists in approved registry
- Check `COPY` paths are relative to build context

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, skip the process" | Simple issues have root causes too |
| "Just try this first" | First fix sets the pattern — do it right |
| "I'll investigate after fixing" | You won't. Investigate first. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause |
| "One more fix attempt" (after 2+ fails) | 3+ failures = step back and rethink |
| "Previous agent broke it, just patch around" | Fix at the source, not at the symptom |

## Red Flags — STOP and Follow Process

If you catch yourself:
- Proposing solutions before reading the error message fully
- Adding multiple fixes at once and hoping one works
- Suppressing warnings instead of fixing underlying issues
- Adding `# type: ignore` without investigating why the type is wrong
- Patching around a design flaw from a previous agent

**ALL of these mean: STOP. Return to Phase 1.**

## Quick Reference

| Phase | Activity | Success Criteria |
|-------|----------|------------------|
| 1. Root Cause | Read errors, reproduce, trace | Understand WHAT and WHY |
| 2. Pattern | Find working examples, compare | Identify key differences |
| 3. Hypothesis | Form theory, test minimally | Confirmed or new hypothesis |
| 4. Fix | Single change, verify, check regressions | Error resolved, nothing else broken |
