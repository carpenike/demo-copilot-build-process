# ADR-XXXX: [Decision Title]

> **Status:** [Proposed | Accepted | Deprecated | Superseded by ADR-XXXX]
> **Date:** YYYY-MM-DD
> **Deciders:** [Names or roles involved in this decision]
> **Project:** [Project name]

---

## Context

Describe the situation that necessitates this decision. What is the problem?
What forces are at play (technical, business, organizational)? Be specific about
constraints that narrow the solution space.

Include any relevant requirements (reference by FR-XXX ID if applicable).

---

## Decision

State the decision clearly in one or two sentences.

> We will use **[chosen option]** for **[purpose]** because **[primary reason]**.

---

## Governance Compliance

> **Required for all technology choice ADRs.**

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Language | Python or Go only | [language] | ✅ / ❌ |
| Framework | [see standards] | [framework] | ✅ / ❌ |
| Infrastructure | [see standards] | [infra] | ✅ / ❌ |

If any row is ❌, an exception must be filed before this ADR is accepted.
Reference: `governance/enterprise-standards.md`

---

## Options Considered

### Option 1: [Name] ← Chosen
**Description:** Brief description.

**Pros:**
- Pro 1
- Pro 2

**Cons:**
- Con 1

---

### Option 2: [Name]
**Description:** Brief description.

**Pros:**
- Pro 1

**Cons:**
- Con 1 (this was the deciding factor against)

---

### Option 3: [Name] (if applicable)
[Same format]

---

## Consequences

### Positive
- List the good outcomes this decision enables

### Negative / Trade-offs
- List what this decision makes harder or more expensive
- Be honest — undocumented trade-offs come back to bite the team

### Risks
- List risks introduced by this decision and any planned mitigations

---

## Implementation Notes

Any specific guidance for the Code Agent on how to implement this decision.
Include:
- Package or library names and versions
- Configuration patterns
- Integration points with other components

---

## References
- [Link to relevant documentation]
- [Related ADRs: ADR-XXXX]
- [Related requirements: FR-XXX]
