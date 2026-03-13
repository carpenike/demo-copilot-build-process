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
| @1-requirements | `1-requirements.agent.md` | Raw input → structured requirements + user stories |
| @2-design | `2-design.agent.md` | Requirements → ADRs + wireframe spec + data model |
| @3-implementation | `3-implementation.agent.md` | ADRs + spec → source code + Dockerfile + OpenAPI |
| @4-test | `4-test.agent.md` | Requirements → test plan + test scaffolding |
| @5-deployment | `5-deployment.agent.md` | ADRs + Dockerfile → Terraform + K8s + CI/CD |
| @6-monitor | `6-monitor.agent.md` | NFRs → SLOs + alerts + runbook + dashboard |

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
credential, or API key — stop, and instead write a reference to Azure Key Vault.

---

## Pipeline Flow

```
Raw Request → @1-requirements → @2-design → @3-implementation → @4-test → @5-deployment → @6-monitor
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
│   │   ├── 1-requirements.agent.md
│   │   ├── 2-design.agent.md
│   │   ├── 3-implementation.agent.md
│   │   ├── 4-test.agent.md
│   │   ├── 5-deployment.agent.md
│   │   └── 6-monitor.agent.md
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
2. Select the **@1-requirements** agent in Copilot Chat and process the project
3. Follow the pipeline in order: @1-requirements → @2-design → @3-implementation → @4-test → @5-deployment → @6-monitor
4. Each stage produces artifacts that feed the next stage

---

## Agent Git Workflow

All agents MUST follow these git practices. This section is inherited by every
agent in the pipeline.

### Before Writing Any Files
1. **Check the current branch.** Run `git branch --show-current`.
2. If you are on `main`, **stop and ask the user** whether to create a feature branch.
   Suggest: `feat/<project>-<agent-stage>` (e.g., `feat/expense-portal-requirements`).
3. If a suitable feature branch already exists, confirm with the user before switching.

### After Completing All Outputs
1. **Stage only the files you produced.** Use explicit paths — never `git add .` or `git add -A`.
2. **Show the user a commit preview** — list the staged files and proposed commit message.
3. **Ask the user to confirm before committing.** Do not commit automatically.
4. **Commit with a conventional commit message** following this format:
   ```
   feat(<project>): <agent-role> — <short summary>

   - Bullet list of artifacts produced
   - Reference to ADR if applicable
   ```
   Use the agent's role as scope context (e.g., `requirements`, `design`, `implementation`,
   `tests`, `deployment`, `monitoring`).
5. **Do NOT push.** The human decides when to push and open a PR.
6. **Print a handoff summary** so the user knows what to do next:
   ```
   --- Handoff Summary ---
   Agent:    @<current-agent>
   Project:  <project-name>
   Branch:   <branch-name>
   Commit:   <short SHA>
   Files:    <list of files produced>
   Next:     Invoke @<next-agent> to continue the pipeline
   ```

### Commit Message Scopes by Agent
| Agent | Scope example |
|-------|---------------|
| @1-requirements | `feat(expense-portal): requirements — ...` |
| @2-design | `feat(expense-portal): design — ...` |
| @3-implementation | `feat(expense-portal): implementation — ...` |
| @4-test | `feat(expense-portal): tests — ...` |
| @5-deployment | `feat(expense-portal): deployment — ...` |
| @6-monitor | `feat(expense-portal): monitoring — ...` |

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
