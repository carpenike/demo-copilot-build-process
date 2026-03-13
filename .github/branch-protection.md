# Branch Protection Rules

This document describes the branch protection configuration for this repository.
These rules are enforced at the GitHub organization level and cannot be bypassed
by individual contributors.

---

## Branch Naming Convention

| Pattern | Purpose | Created by |
|---------|---------|-----------|
| `main` | Production-ready code | Protected |
| `feat/<ticket-id>-short-description` | New features | Developer |
| `fix/<ticket-id>-short-description` | Bug fixes | Developer |
| `chore/<description>` | Maintenance tasks | Developer |
| `release/<version>` | Release preparation | Release manager |

**Examples:**
- `feat/PROJ-123-user-authentication`
- `fix/PROJ-456-null-pointer-on-empty-cart`
- `chore/upgrade-dependencies-q1-2026`

---

## `main` Branch Protection Rules

```yaml
# GitHub branch protection settings for `main`
required_status_checks:
  strict: true  # Branch must be up-to-date before merging
  contexts:
    - lint
    - test
    - security
    - build
    - integration

required_pull_request_reviews:
  required_approving_review_count: 2
  dismiss_stale_reviews: true
  require_code_owner_reviews: true

restrictions:
  push_restrictions: []  # No direct pushes; PRs only

merge_options:
  allow_squash_merge: true    # Only merge method allowed
  allow_merge_commit: false
  allow_rebase_merge: false

delete_branch_on_merge: true
```

---

## Merge Strategy

**Squash merge only.** Every feature branch squashes to a single commit on main.

This keeps `main` history clean and readable. The squash commit message follows
conventional commits format:

```
feat(scope): short description of what changed

- Bullet summary of significant changes
- Reference to ADR if architectural decision was involved

Closes #[issue-number]
```

---

## CODEOWNERS

Certain paths require approval from specific teams in addition to the standard 2 reviewers:

```
# Governance changes require Platform Engineering sign-off
/governance/                    @org/platform-engineering

# Infrastructure changes require DevOps sign-off
/infrastructure/                @org/devops
/.github/workflows/             @org/devops

# ADR changes require Architecture Guild sign-off
/docs/adr/                      @org/architecture-guild

# Agent configuration changes require Platform Engineering sign-off
/.github/agents/                @org/platform-engineering
```
