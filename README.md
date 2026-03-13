# Agentic Build Pipeline — Demo Environment

A structured environment for demonstrating enterprise-grade agentic software
development using GitHub Copilot (Claude Opus) in VSCode.

## The Concept

Rather than six independent AI agents, this pipeline is six **specialized roles**
that a single AI assistant (GitHub Copilot with Claude Opus) steps into at each
stage of the software development lifecycle. The power comes from:

1. **Role specialization** — each `.github/agents/<role>.agent.md` gives the model
   focused instructions, inputs, and output formats for one stage
2. **Artifact chaining** — each stage's output is the next stage's input,
   creating a traceable, reviewable audit trail
3. **Enterprise governance** — `governance/enterprise-standards.md` constrains
   every agent, so technology decisions stay within approved boundaries automatically

## Pipeline at a Glance

```
Raw Request → @1-requirements → @2-design → @3-implementation → @4-test → @5-deployment → @6-monitor
```

See `governance/agent-pipeline-overview.md` for the full diagram.

## Quick Start (Demo Flow)

**Step 1:** Drop a feature request into `projects/<project>/input/request.md`

**Step 2:** In Copilot Chat, select the **@1-requirements** agent from the agent
picker and give it the project to process

**Step 3:** Review and save the output to `projects/<project>/requirements/`

**Step 4:** Continue through each agent role in sequence (@2-design → @3-implementation → @4-test → @5-deployment → @6-monitor)

## Key Files

| File | Purpose |
|------|---------|
| `.github/copilot-instructions.md` | Workspace instructions (auto-loaded by Copilot) |
| `DEMO-SCRIPT.md` | Step-by-step demo script with prompts and talking points |
| `governance/enterprise-standards.md` | Non-negotiable constraints for all agents |
| `.github/agents/*.agent.md` | Copilot custom agent definitions (appear in agent picker) |
| `templates/` | Reusable output templates (all 6 stages) |
| `.github/PULL_REQUEST_TEMPLATE.md` | PR checklist enforcing standards |
| `.github/workflows/ci-template.yml` | Python CI pipeline template |
| `.github/workflows/ci-template-go.yml` | Go CI pipeline template |

## Included Projects

| Project | Purpose |
|---------|---------|
| `projects/expense-portal/` | **Primary demo project** — Finance BRD, run the pipeline live |
| `projects/example-ticket-app/` | **Golden path reference** — completed pipeline output to show the end state |

## Enterprise Standards Summary

- **Languages:** Python 3.11+ and Go 1.22+ only
- **Containers:** Docker (multi-stage builds, non-root, distroless base)
- **Orchestration:** Kubernetes on AKS
- **CI/CD:** GitHub Actions with mandatory lint → test → security → build → integration stages
- **Secrets:** Azure Key Vault only; never in code or config files
- **Observability:** Structured JSON logs + Prometheus metrics + OpenTelemetry traces (all via Azure Monitor)
