# Agentic Build Pipeline — Overview

This document describes how the six-agent pipeline works end-to-end and how
artifacts flow between stages. Every agent is a native Copilot custom agent
defined in `.github/agents/*.agent.md`, with workspace-wide context from
`.github/copilot-instructions.md` and constrained by
`governance/enterprise-standards.md`.

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
        DEP_OUT["Output: terraform/\n+ GitHub Actions workflows"]
    end

    DEP --> MON

    subgraph MON ["@6-monitor"]
        direction LR
        MON_IN["Input: requirements.md\n+ deployed service config"]
        MON_OUT["Output: runbook.md\n+ alert-rules.yaml + dashboards"]
    end
```

---

## Using the Pipeline in GitHub Copilot (VSCode)

Agents are defined in `.github/agents/` and appear automatically in the
Copilot Chat agent picker. Select an agent by name to invoke it.

**Recommended demo flow:**

1. Drop a raw feature request into `projects/<project-name>/input/request.md`
2. Select **@1-requirements** in the agent picker and process the request
3. Save output to `projects/<project-name>/requirements/`
4. Select **@2-design** → feed requirements → save ADRs to `docs/adr/`
5. Select **@3-implementation** → begin coding against the ADR
6. Select **@4-test** → generate test plan
7. Select **@5-deployment** → generate IaC + workflows
8. Select **@6-monitor** → generate runbook + alert config

---

## Artifact Ownership by Stage

| Artifact | Producing Agent | Consuming Agent(s) |
|----------|----------------|-------------------|
| `requirements.md` | Requirements | Design, Test, Monitor |
| `user-stories.md` | Requirements | Design, Test |
| `docs/adr/ADR-XXXX-*.md` | Design | Code, Deployment |
| `wireframe-spec.md` | Design | Code |
| Source code | Implementation (@3-implementation) | Test, Deployment |
| `openapi.yaml` | Implementation (@3-implementation) | Test, Monitor |
| `Dockerfile` | Implementation (@3-implementation) | Deployment |
| `test-plan.md` | Test | — (human review) |
| `terraform/` | Deployment | Monitor |
| `runbook.md` | Monitor | — (ops team) |
| `alert-rules.yaml` | Monitor | — (ops team) |
