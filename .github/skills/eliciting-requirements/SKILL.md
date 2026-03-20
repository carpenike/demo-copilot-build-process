---
name: eliciting-requirements
description: "Use when a user has a vague idea or stream-of-consciousness but no written input document — guides a structured conversation to capture the problem, users, success criteria, and constraints, then produces the input file for @1-requirements."
---

# Eliciting Requirements

## Overview

Help a user go from a vague idea to a written input document through structured
conversation. This skill sits **before** the pipeline — it produces the raw
input that @1-requirements will later transform into formal FR/NFR format.

**Core principle:** Ask, don't assume. Capture intent before structure.

## When to Use

- User says something like "I need an app that..." or "we should build..."
- User has a rough idea but no written document
- `projects/<project>/input/` is empty or doesn't exist yet
- @1-requirements has no input file to process

**Not needed when:**
- A written document already exists in `input/` (even informal notes)
- The user pastes a BRD, spec, or requirements doc directly

## The Process

### 1. Understand the Core Problem

Start with the most important question:

> "What problem are you trying to solve, and why does it need solving now?"

Listen for:
- The pain point (what's broken or missing today)
- The trigger (why now, not 6 months ago)
- Who feels the pain most

### 2. Identify Users and Stakeholders

One question at a time:

> "Who will use this? Are there different types of users with different needs?"

Capture:
- Primary users (who interacts daily)
- Secondary users (occasional, admin, reporting)
- Stakeholders (who approves, who pays, who's accountable)

### 3. Define Success

> "If this project goes perfectly, what does the world look like 6 months after launch?"

This surfaces:
- Measurable outcomes (not vague "better")
- Business metrics that matter
- The difference between "nice to have" and "must have"

### 4. Explore Scope and Constraints

> "What is explicitly NOT part of this? What are the hard constraints?"

Capture:
- What's out of scope (prevents scope creep)
- Budget or timeline constraints
- Regulatory or compliance requirements
- Integration requirements (what existing systems does it touch?)

### 5. Capture Non-Functional Expectations

> "How many users do you expect? What happens if the system is down for an hour?"

Cover:
- Expected scale (users, transactions, data volume)
- Availability expectations (business hours only? 24/7?)
- Performance expectations (real-time? batch is fine?)
- Security sensitivity (public data? PII? financial?)

### 6. Surface Assumptions and Open Questions

> "What are you assuming that might not be true? What questions do you still have?"

This catches:
- Hidden assumptions that need validation
- Dependencies on other teams or systems
- Decisions that need executive input

## Output

After the conversation, produce ONE of:

- `projects/<project>/input/request.md` — informal, stream-of-consciousness
  style (for quick/small projects)
- `projects/<project>/input/business-requirements.md` — structured BRD format
  (for larger/formal projects)

**Use the format that matches the conversation.** Don't over-formalize a casual
conversation, and don't under-structure a detailed one.

### Minimal Output Template

```markdown
# [Project Name]

## Problem
[What's broken or missing, and why it matters now]

## Users
[Who uses it, what are their roles]

## Success Criteria
[Measurable outcomes — what does "done" look like]

## Scope
**In scope:** [What this project covers]
**Out of scope:** [What it explicitly does NOT cover]

## Constraints
[Budget, timeline, regulatory, technical constraints]

## Non-Functional Expectations
[Scale, availability, performance, security]

## Open Questions
[Unresolved items that need answers before or during design]
```

## Key Principles

- **One question at a time** — don't dump a questionnaire
- **Listen more than talk** — the user knows their problem better than you
- **Capture intent, not solutions** — "I need to track expenses" not "build a REST API"
- **Flag assumptions** — if the user says something that implies a technology
  choice, note it but don't embed it in the requirements
- **Know when to stop** — you don't need perfect detail; @1-requirements will
  structure and refine what you capture

## Integration with Pipeline

- This skill produces the input file for `projects/<project>/input/`
- After the file is written, hand off to **@1-requirements** to structure it
- The user reviews the input file before proceeding — it's their intent captured,
  not yours
