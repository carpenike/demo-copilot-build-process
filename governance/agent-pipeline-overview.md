# Agentic Build Pipeline — Overview

This document describes how the seven-agent pipeline works end-to-end and how
artifacts flow between stages. Every agent is a native Copilot custom agent
defined in [`.github/agents/`](../.github/agents/), with workspace-wide context from
[`.github/copilot-instructions.md`](../.github/copilot-instructions.md) and constrained by
[`governance/enterprise-standards.md`](enterprise-standards.md).

---

## Pipeline Diagram

```mermaid
flowchart TD
    Input["Stakeholder Input\n(raw feature request / problem statement)"]

    Input --> REQ

    subgraph REQ ["@1-requirements"]
        direction LR
        REQ_IN["Input: Raw request"]
        REQ_OUT["Output: requirements.md\n+ user-stories.md"]
    end

    REQ --> DES

    subgraph DES ["@2-design"]
        direction LR
        DES_IN["Input: requirements.md\n+ enterprise-standards.md"]
        DES_OUT["Output: ADRs\n+ wireframe-spec.md"]
    end

    DES --> IMP

    subgraph IMP ["@3-implementation"]
        direction LR
        IMP_IN["Input: ADRs + wireframe-spec\n+ enterprise-standards"]
        IMP_OUT["Output: Source code\n+ openapi.yaml + Dockerfile"]
    end

    IMP --> TST

    subgraph TST ["@4-test"]
        direction LR
        TST_IN["Input: requirements.md\n+ source code"]
        TST_OUT["Output: test-plan.md\n+ test scaffolding"]
    end

    TST --> DEP

    subgraph DEP ["@5-deployment"]
        direction LR
        DEP_IN["Input: ADRs + Dockerfile\n+ enterprise-standards"]
        DEP_OUT["Output: Bicep modules\n+ GitHub Actions workflows"]
    end

    DEP --> MON

    subgraph MON ["@6-monitor"]
        direction LR
        MON_IN["Input: requirements.md\n+ deployed service config"]
        MON_OUT["Output: runbook.md\n+ alert-rules.bicep + dashboards"]
    end

    MON --> REV

    subgraph REV ["@7-review"]
        direction LR
        REV_IN["Input: All artifacts\n+ enterprise-standards.md"]
        REV_OUT["Output: review-report.md\n+ auto-fixes"]
    end
```

---

## Using the Pipeline in GitHub Copilot (VSCode)

Agents are defined in [`.github/agents/`](../.github/agents/) and appear automatically in the
Copilot Chat agent picker. Select an agent by name to invoke it.

> [!IMPORTANT]
> Each agent validates that the previous agent's artifacts exist before starting.
> If inputs are missing, the agent will stop and tell you which earlier agent to
> run first. This ensures the pipeline completes successfully in order.

**Recommended flow:**

1. Drop a feature request into `projects/<project>/input/` (any format — informal notes or formal BRD)
2. Select **@1-requirements** in the agent picker
3. Review the output, then continue with each agent in order:
   **@2-design** → **@3-implementation** → **@4-test** → **@5-deployment** → **@6-monitor** → **@7-review**
4. Each agent verifies its outputs before handing off to the next stage

---

## Skills — Cross-Cutting Methodology

Skills are reusable behavioral patterns in [`.github/skills/`](../.github/skills/)
that are shared across agents. They define **how** agents work (methodology,
discipline, debugging), while agent files define **what** agents produce.

| Skill | Used By | Purpose |
|-------|---------|---------|
| `verification-before-completion` | All agents | Evidence before claims — run commands and cite output |
| `systematic-debugging` | @3, @4, @5, @7 | 4-phase root cause investigation |
| `test-driven-development` | @3 | RED-GREEN-REFACTOR cycle |
| `brainstorming` | @2 | Explore alternatives before committing to design |

---

## Artifact Ownership by Stage

| Artifact | Producing Agent | Consuming Agent(s) |
|----------|----------------|-------------------|
| `requirements.md` | @1-requirements | @2-design, @4-test, @6-monitor |
| `user-stories.md` | @1-requirements | @2-design, @4-test |
| `docs/adr/ADR-XXXX-*.md` | @2-design | @3-implementation, @5-deployment |
| `wireframe-spec.md` | @2-design | @3-implementation, @4-test |
| `data-model.md` | @2-design | @3-implementation |
| `architecture-overview.md` | @2-design | @3-implementation |
| Source code | @3-implementation | @4-test, @5-deployment |
| `openapi.yaml` | @3-implementation | @4-test, @6-monitor |
| `Dockerfile` | @3-implementation | @5-deployment |
| `test-plan.md` | @4-test | @5-deployment (prerequisite check) |
| `*.bicep`, `k8s/` | @5-deployment | @6-monitor |
| CI/CD workflows | @5-deployment | — (GitHub Actions) |
| `runbook.md` | @6-monitor | — (ops team) |
| `alert-rules.bicep` | @6-monitor | — (ops team) |
| `slo-definitions.md` | @6-monitor | — (ops team) |
| `dashboard-spec.md` | @6-monitor | — (ops team) |
| `PREREQUISITES.md` | @5-deployment | — (platform team) |
| `review-report.md` | @7-review | — (PR reviewers) |
