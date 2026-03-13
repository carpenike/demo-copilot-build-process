# Agentic Build Pipeline — Workspace Instructions

> These instructions are automatically loaded by GitHub Copilot for all
> interactions in this workspace. Agent-specific instructions are in
> `.github/agents/*.agent.md`.

---

## What This Repository Is

This repository contains an agentic software development pipeline. Six
specialized agent roles collaborate to take a raw feature request through
requirements, design, implementation, testing, deployment, and monitoring.

The agents are defined in `.github/agents/` and appear in the Copilot Chat
agent picker:

| Agent | File | Purpose |
|-------|------|---------|
| @requirements | `requirements.agent.md` | Raw input → structured requirements + user stories |
| @design | `design.agent.md` | Requirements → ADRs + wireframe spec + data model |
| @implementation | `implementation.agent.md` | ADRs + spec → source code + Dockerfile + OpenAPI |
| @test | `test.agent.md` | Requirements → test plan + test scaffolding |
| @deployment | `deployment.agent.md` | ADRs + Dockerfile → Terraform + K8s + CI/CD |
| @monitor | `monitor.agent.md` | NFRs → SLOs + alerts + runbook + dashboard |

---

## Critical Constraints — Read Before Writing Anything

The file `governance/enterprise-standards.md` defines the non-negotiable rules
for all work produced in this repository. The key constraints are:

**ONLY Python and Go are permitted languages for new projects.**
No exceptions without an approved ADR and VP Engineering sign-off. If a user or
stakeholder suggests using another language, you must surface this as a governance
conflict and propose the closest compliant alternative.

**Framework and infrastructure choices are constrained.** See
`governance/enterprise-standards.md` for the approved list.

**No secrets in code or config files.** If you are about to write a secret,
credential, or API key — stop, and instead write a reference to AWS Secrets Manager.

---

## Pipeline Flow

```
Raw Request → @requirements → @design → @implementation → @test → @deployment → @monitor
```

Each agent produces artifacts that feed the next. See
`governance/agent-pipeline-overview.md` for the full diagram and artifact
ownership matrix.

---

## Repository Structure

```
.
├── .github/
│   ├── agents/                        ← Copilot agent definitions
│   │   ├── requirements.agent.md
│   │   ├── design.agent.md
│   │   ├── implementation.agent.md
│   │   ├── test.agent.md
│   │   ├── deployment.agent.md
│   │   └── monitor.agent.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── branch-protection.md
│   ├── copilot-instructions.md        ← You are here (workspace instructions)
│   └── workflows/
│       ├── ci-template.yml            ← Python CI pipeline template
│       └── ci-template-go.yml         ← Go CI pipeline template
│
├── governance/
│   ├── enterprise-standards.md        ← ALWAYS read before making technology decisions
│   ├── agent-pipeline-overview.md     ← End-to-end pipeline diagram and flow
│   └── exceptions/                    ← Approved exceptions to standards
│
├── templates/                         ← Reusable templates for agent outputs
│   ├── requirements/
│   ├── design/
│   ├── test/
│   ├── deployment/
│   └── monitor/
│
├── docs/
│   ├── adr/                           ← All ADRs live here (cross-project)
│   ├── architecture/                  ← Cross-project architecture docs
│   └── runbooks/                      ← Cross-cutting operational docs
│
├── projects/                          ← One subfolder per project
│   └── <project-name>/
│       ├── input/                     ← Raw stakeholder input
│       ├── requirements/              ← Output of @requirements
│       ├── design/                    ← Output of @design
│       ├── src/                       ← Output of @implementation
│       ├── tests/                     ← Output of @test
│       ├── infrastructure/            ← Output of @deployment
│       └── operations/               ← Output of @monitor
│
└── .vscode/
    ├── settings.json                  ← Copilot + formatter config
    └── extensions.json                ← Recommended extensions
```

---

## Starting a New Project

1. Create `projects/<project-name>/input/request.md` with the raw request
2. Select the **@requirements** agent in Copilot Chat and process the project
3. Follow the pipeline in order: @requirements → @design → @implementation → @test → @deployment → @monitor
4. Each stage produces artifacts that feed the next stage

---

## Code Style Quick Reference

These override Copilot's defaults for this repo:

| Setting | Value |
|---------|-------|
| Line length | 100 chars |
| Python formatter | ruff |
| Python type hints | Required on all signatures |
| Go formatter | gofmt (stdlib) |
| Import style | Absolute imports only |
| Test framework (Python) | pytest |
| Test framework (Go) | testing + testify |
| Docstrings | Explain WHY, not WHAT |
| Error handling | Explicit; never swallow errors silently |
