# Agentic Build Pipeline — Workspace Instructions

> These instructions are automatically loaded by GitHub Copilot for all
> interactions in this workspace. Agent-specific instructions are in
> `.github/agents/*.agent.md`.

---

## What This Repository Is

This repository contains an agentic software development pipeline. Seven
specialized agent roles collaborate to take a raw feature request through
requirements, design, implementation, testing, deployment, monitoring, and
final compliance review.

The agents are defined in `.github/agents/` and appear in the Copilot Chat
agent picker:

| Agent | File | Purpose |
|-------|------|---------|
| @1-requirements | `1-requirements.agent.md` | Raw input → structured requirements + user stories |
| @2-design | `2-design.agent.md` | Requirements → ADRs + wireframe spec + data model |
| @3-implementation | `3-implementation.agent.md` | ADRs + spec → source code + Dockerfile + OpenAPI |
| @4-test | `4-test.agent.md` | Requirements → test plan + test scaffolding |
| @5-deployment | `5-deployment.agent.md` | ADRs + Dockerfile → Bicep + CI/CD + prerequisites |
| @6-monitor | `6-monitor.agent.md` | NFRs → SLOs + Azure Monitor alerts + runbook + dashboard |
| @7-review | `7-review.agent.md` | Full compliance review against enterprise standards |

---

## Critical Constraints — Read Before Writing Anything

The file `governance/enterprise-standards.md` defines the non-negotiable rules
for all work produced in this repository. The key constraints are:

**ONLY Python and Go are permitted languages for new projects.**
No exceptions without an approved ADR and VP Engineering sign-off. If a user or
stakeholder suggests using another language, you must surface this as a governance
conflict and propose the closest compliant alternative.

**Azure PaaS-first.** All technology decisions MUST prefer Microsoft first-party
Azure PaaS services. Use Azure Container Apps over AKS, Azure Monitor over
Prometheus/Grafana, OpenTelemetry + Azure Monitor exporter over standalone
Prometheus client libraries. See `governance/enterprise-standards.md` for the
complete Cloud Service Preference Policy.

**Framework and infrastructure choices are constrained.** See
`governance/enterprise-standards.md` for the approved list.

**Code quality is enforced.** All Python projects must use ruff (with the
mandatory rule set), mypy strict mode, and 80% test coverage. See
`governance/enterprise-standards.md` § Code Quality Standards.

**No secrets in code or config files.** If you are about to write a secret,
credential, or API key — stop, and instead write a reference to Azure Key Vault.

---

## Pipeline Flow

```
Raw Request → @1-requirements → @2-design → @3-implementation → @4-test → @5-deployment → @6-monitor → @7-review
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
│   │   ├── 6-monitor.agent.md
│   │   └── 7-review.agent.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── branch-protection.md
│   ├── copilot-instructions.md        ← You are here (workspace instructions)
│   └── workflows/
│       ├── ci-template.yml.template   ← Python CI pipeline template
│       ├── ci-template-go.yml.template ← Go CI pipeline template
│       └── cd-template.yml.template   ← Bicep CD pipeline template
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
3. Follow the pipeline in order: @1-requirements → @2-design → @3-implementation → @4-test → @5-deployment → @6-monitor → @7-review
4. After @5-deployment completes, it will offer to run the bootstrap script
   to provision Azure resources. You can also run it manually:
   ```bash
   ./scripts/check-prerequisites.sh <project-name> dev \
       --from-config projects/<project-name>/infrastructure/bootstrap.conf --fix
   ```
   The `bootstrap.conf` file is generated by @5-deployment and defines which
   Azure services the project needs. The `--fix` flag auto-creates missing resources.
5. Each stage produces artifacts that feed the next stage

---

## Agent Git Workflow

All agents MUST follow these git practices. This section is inherited by every
agent in the pipeline.

### Before Writing Any Files
1. **Check the current branch.** Run `git branch --show-current`.
2. If you are on `main`, **stop and ask the user** whether to create a feature branch.
   Suggest: `feat/<project>` (e.g., `feat/expense-portal`). All agents in the
   pipeline commit to the **same branch** — each agent's work is separated by a
   distinct commit, not a separate branch.
3. If a feature branch for this project already exists (e.g., created by a prior
   agent in the pipeline), **continue on it** — do not create a new branch.

### After Completing All Outputs
1. **Stage only the files you produced.** Use explicit paths — never `git add .` or `git add -A`.
2. **Run local code quality checks (Python projects).** Before showing the commit
   preview, run these commands from the project's `src/` directory and fix any
   errors. Repeat until all pass:
   ```bash
   cd projects/<project>/src
   uvx ruff check app/          # lint — must exit 0
   uvx ruff format --check app/ # format — must exit 0
   ```
   If `uvx` is not available, try `ruff` directly or `python3 -m ruff`.
   Do NOT commit code that fails these checks — fix and re-verify.
3. **Show the user a commit preview** — list the staged files and proposed commit message.
4. **Ask the user to confirm before committing.** Do not commit automatically.
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
| @7-review | `feat(expense-portal): review — ...` |

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
