# Demo Script — Agentic Build Pipeline

> **Prep time:** 5 minutes | **Demo time:** 30–45 minutes
> **Pre-requisite:** VS Code with GitHub Copilot (Claude Opus) enabled

---

## Before You Start

1. Open VS Code in this repo's root directory
2. Confirm Copilot is active and using Claude Opus (check status bar)
3. Have these files open in tabs for quick reference:
   - `.github/copilot-instructions.md`
   - `governance/enterprise-standards.md`
   - `.github/agents/requirements.agent.md`
4. **Show the agent picker** — agents appear automatically because they’re
   in `.github/agents/` with proper YAML frontmatter

---

## The Story

> *"We're going to take a real business requirements document — written by
> Finance, not engineers — and run it through an AI-powered pipeline that
> produces requirements, architecture decisions, code, tests, infrastructure,
> and monitoring config. Every step is constrained by enterprise standards
> that the AI enforces automatically."*

---

## Stage 1: Set the Scene (3 min)

**Talk track:** Explain the repo structure and the concept of specialized agent roles.

**Show:**
- Open `.github/copilot-instructions.md` — point out the critical constraints section
- Open `governance/enterprise-standards.md` — highlight the language policy (Python/Go only)
- Briefly show the `.github/agents/` folder — six agent files, each with YAML frontmatter
  that makes them appear in the Copilot Chat agent picker automatically
- **Key demo moment:** Open the agent picker in Copilot Chat and show all six agents listed

**Key point:** *"These agents appear automatically because they’re defined as native
Copilot custom agents. Each has restricted tools — the Requirements Agent can read
and write files but can’t run terminal commands. The Code Agent can. This is
role-based access control for AI."*

---

## Stage 2: Requirements Agent (8 min)

**Show the raw input:**
Open `projects/expense-portal/input/business-requirements.md`. Point out that
this is a real-world BRD — unstructured, from a business team, with constraints
and open questions baked in.

**Prompt to paste in Copilot Chat:**
```
@requirements Process the input at projects/expense-portal/input/business-requirements.md.

Produce:
1. projects/expense-portal/requirements/requirements.md
2. projects/expense-portal/requirements/user-stories.md
```

> **Note:** No need to manually load instructions — the @requirements
> agent loads its role instructions and the workspace context automatically.

**What to highlight as it runs:**
- The agent structures unambiguous FR-XXX / NFR-XXX requirements from prose
- User stories get Gherkin acceptance criteria
- The governance flags section catches any conflicts with enterprise standards
- Non-functional requirements have *measurable* targets, not vague words

**Pause point:** *"Notice it didn't just summarize the doc — it decomposed it
into testable requirements with acceptance criteria. And it flagged anything
that conflicts with our enterprise standards."*

---

## Stage 3: Design Agent (8 min)

**Prompt to paste in Copilot Chat:**
```
@design The requirements are at:
- projects/expense-portal/requirements/requirements.md
- projects/expense-portal/requirements/user-stories.md

Produce ADRs in docs/adr/ and design documents in projects/expense-portal/design/.
```

**What to highlight:**
- ADRs include a **Governance Compliance** table — each technology choice is
  checked against standards
- The wireframe spec defines exact API contracts (request/response schemas,
  error codes, auth requirements)
- Data model uses mermaid ER diagrams
- Architecture overview shows component diagram with security boundaries

**Pause point:** *"Every ADR proves the technology choice is compliant. If a
stakeholder asked for MongoDB, the agent would either reject it or document
the exception process. The design is a contract — detailed enough that a
developer (human or AI) can implement without ambiguity."*

**Show the golden path:** Open `projects/example-ticket-app/design/` to show
what completed Design Agent output looks like.

---

## Stage 4: Code Agent (8 min)

**Prompt to paste in Copilot Chat:**
```
@implementation Begin implementing the expense-portal service in
projects/expense-portal/src/ following the Python project structure.

Start with: project scaffolding, config, health endpoints, and the core
data models.
```

**What to highlight:**
- Code follows the exact structure from AGENT.md (app/api/, app/core/, app/models/, etc.)
- `/health`, `/ready`, `/metrics` endpoints appear automatically
- No secrets in code — config references Secrets Manager
- Type hints on every signature, async throughout
- Dockerfile uses multi-stage build with non-root user

**Key point:** *"The Code Agent doesn't invent architecture — it executes
the decisions from the ADRs. If the design says FastAPI, it builds FastAPI.
If it spots a design flaw, it surfaces it instead of silently working around it."*

---

## Stage 5: Test Agent (5 min, can be abbreviated)

**Prompt to paste in Copilot Chat:**
```
@test Generate a test plan and test scaffolding for the expense-portal project.
Work from the requirements and user stories, not the implementation.
```

**What to highlight:**
- Test plan maps every FR-XXX to test cases
- Tests derived from *requirements*, not code (avoids circular coverage)
- Auth boundary tests are automatic (401, 403 scenarios)
- Test coverage target: 80% on core logic

---

## Stage 6: Deployment Agent (5 min, can be abbreviated)

**Prompt:**
```
@deployment Generate Terraform modules and Kubernetes manifests for the
expense-portal. Generate CI and CD GitHub Actions workflows.
```

**What to highlight:**
- K8s manifests include: HPA, PDB, NetworkPolicy, resource limits
- CI pipeline has all 5 required stages (lint → test → security → build → integration)
- Secrets via External Secrets Operator — never in manifests

---

## Stage 7: Monitor Agent (5 min, can be abbreviated)

**Prompt:**
```
@monitor Generate operational artifacts for the expense-portal service.
```

**What to highlight:**
- SLOs derived from the NFR targets (not arbitrary numbers)
- Every alert has a `runbook_url`
- Runbook has step-by-step triage for each alert

---

## Closing Talking Points

1. **Traceability:** Every artifact links back — code implements ADRs, tests
   verify requirements, alerts match SLOs from NFRs
2. **Governance enforcement:** The AI can't go off-rails because constraints
   are embedded in its context at every stage
3. **Audit trail:** Every decision is documented in an ADR with alternatives
   considered and trade-offs acknowledged
4. **Reproducibility:** A new team member can re-run any stage and get
   consistent, standards-compliant output
5. **Human in the loop:** The AI produces artifacts; humans review and approve
   before moving to the next stage

---

## FAQ / Anticipated Questions

**Q: Does this replace developers?**
A: No. It accelerates the structured, repeatable parts of the SDLC. Humans
review every artifact and make judgment calls the AI surfaces as questions.

**Q: What if the AI makes a mistake?**
A: Each stage is reviewable before feeding the next. The governance constraints
catch policy violations automatically. Mistakes in logic are caught the same
way you'd catch them in a code review — but you get to review earlier.

**Q: Can this work with other models?**
A: The agent framework is model-agnostic. The `.agent.md` files define the
process and tool restrictions; Copilot routes to them automatically. You can
even set a `model:` field in the frontmatter to pin a specific model.

**Q: How do you handle exceptions to the standards?**
A: Show `governance/exceptions/README.md` — there's a documented process
with VP sign-off and an ADR requirement.
