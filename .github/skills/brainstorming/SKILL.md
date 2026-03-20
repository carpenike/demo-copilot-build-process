---
name: brainstorming
description: "Use when refining design approaches before producing ADRs — explores 2-3 architectural alternatives with trade-offs through Socratic questioning. Requires user approval before committing to a design direction."
---

# Brainstorming Ideas Into Designs

## Overview

Help turn requirements into well-considered designs through structured
exploration. Don't jump to the first viable solution — explore alternatives,
present trade-offs, and get explicit user approval before producing design
artifacts.

**Core principle:** Explore before committing. Present options, not conclusions.

## Hard Gate

```
DO NOT produce ADRs, wireframe specs, or data models until you have
presented design alternatives and the user has approved a direction.
```

This applies regardless of how "obvious" the design seems.

## When to Use

**Always during @2-design** — before writing any ADR or design document.

**Also useful when:**
- @3-implementation discovers a design flaw and needs to route back
- A stakeholder requirement is ambiguous and has multiple valid interpretations
- The governance constraints create interesting design tension

## The Process

### 1. Understand the Problem Space

- Read the requirements and user stories carefully
- Read `governance/enterprise-standards.md` to understand constraints
- Identify the key decision points (compute, storage, auth, integration patterns)

### 2. Ask Clarifying Questions — One at a Time

Don't overwhelm with a list of 10 questions. Ask one question per message.

**Prefer multiple choice** when possible:
> "For the approval workflow, I see two patterns that fit within our Azure PaaS constraints:
> A) Event-driven with Azure Service Bus (async, decoupled)
> B) Direct API calls with polling (simpler, synchronous)
> Which fits your latency requirements better?"

**Focus on understanding:**
- What does success look like?
- What are the non-negotiable constraints?
- What are the acceptable trade-offs?

### 3. Propose 2-3 Approaches with Trade-offs

For each significant decision point, present options:

```markdown
## Data Storage: Three Approaches

### Option A: Azure Database for PostgreSQL (Recommended)
- ✅ Relational model fits expense/approval data naturally
- ✅ ACID transactions for financial data
- ✅ Azure PaaS-first compliance
- ⚠️ Requires connection pooling for ACA scale-to-zero

### Option B: Azure Cosmos DB
- ✅ Flexible schema for varied document types
- ✅ Built-in global distribution
- ❌ Overkill for single-region deployment
- ❌ Higher cost for relational query patterns

### Option C: Azure SQL Database
- ✅ Full SQL Server feature set
- ✅ Azure PaaS compliant
- ⚠️ Enterprise standards prefer PostgreSQL for new projects

**Recommendation:** Option A — PostgreSQL is the natural fit for structured
financial data, and it's the preferred database in our enterprise standards.
```

**Always lead with your recommendation and explain why.**

### 4. Get User Approval Before Proceeding

After presenting approaches, ask explicitly:
> "Does this direction look right? Any adjustments before I produce the
> ADRs and design documents?"

**Wait for confirmation.** Don't proceed on silence.

### 5. Transition to Design Artifacts

Once approved, produce the ADRs and design documents. The approved direction
becomes the "Decision" in each ADR, and the alternatives become the
"Options Considered" section.

## Key Principles

- **One question at a time** — don't overwhelm
- **Multiple choice preferred** — easier to evaluate than open-ended
- **Lead with recommendation** — explain your reasoning
- **Explore alternatives** — always present 2-3 approaches
- **Respect governance** — flag approaches that conflict with enterprise standards
- **Incremental validation** — get approval at each major decision point

## Anti-Patterns

| Bad Pattern | Better Approach |
|-------------|-----------------|
| Dump all questions at once | One question per message |
| Present only one option | Always 2-3 with trade-offs |
| Skip to producing ADRs | Get explicit approval first |
| "This is obviously the right choice" | Explain WHY, let user decide |
| Ignore governance constraints | Flag conflicts, propose compliant alternatives |

## Integration with Pipeline

- **@2-design** uses this skill before producing any design artifacts
- The output of brainstorming feeds directly into ADR writing
- Approved alternatives become the "Options Considered" in ADRs
- If @3-implementation finds a design flaw, route back here before redesigning
