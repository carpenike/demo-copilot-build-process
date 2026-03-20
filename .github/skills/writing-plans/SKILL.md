---
name: writing-plans
description: "Use when @3-implementation has a complex feature to build — breaks implementation into bite-sized tasks (2-5 minutes each) with exact file paths, complete code, and verification steps before coding begins."
---

# Writing Plans

## Overview

Write comprehensive implementation plans before touching code. Break work into
bite-sized tasks that each produce a verifiable result. Assume the implementer
has zero context for the codebase — document everything needed: which files to
touch, exact code, how to test it.

**Core principle:** Plan the work, then work the plan. No improvising.

## When to Use

**During @3-implementation** when:
- Implementing more than 2-3 files
- Building a new service from scratch
- The wireframe-spec defines multiple endpoints
- The feature touches multiple layers (API, models, services, config)

**Not needed for:**
- Single-file scaffolding (config.py, pyproject.toml)
- Dockerfile or Makefile generation
- Minor tweaks to existing code

## Plan Before You Build

Before writing any implementation code, present the user with a plan:

1. **Read all inputs** — ADRs, wireframe-spec, data-model, requirements
2. **Map the file structure** — which files will be created or modified
3. **Order the tasks** — dependencies first (models → services → API routes)
4. **Break into bite-sized tasks** — each task is one logical unit (2-5 minutes)
5. **Present to user for approval** — don't start coding until the plan is confirmed

## Task Structure

Each task in the plan should follow this format:

```markdown
### Task N: [Component Name]

**Files:**
- Create: `app/models/expense.py`
- Create: `app/api/expenses.py`
- Test: `tests/test_expenses.py`

**Steps:**
1. Write failing test for [specific behavior]
2. Run test — verify it fails with [expected error]
3. Implement [specific function/endpoint]
4. Run test — verify it passes
5. Run `uvx ruff check app/` — verify clean

**Depends on:** Task N-1 (models must exist before API routes)
```

## Task Granularity

**Each task is ONE logical unit:**
- "Create the Expense SQLAlchemy model" — one task
- "Add the POST /v1/expenses endpoint" — one task
- "Add validation for expense amount limits" — one task

**NOT:**
- "Implement the entire expense API" — too large
- "Add a blank line" — too small

## Task Ordering

Follow dependency order:

1. **Configuration** — config.py, pyproject.toml dependencies
2. **Data models** — SQLAlchemy ORM models, Pydantic schemas
3. **Database migrations** — Alembic migration files
4. **Service layer** — business logic in core/
5. **API routes** — FastAPI routers
6. **Health/ready endpoints** — required endpoints
7. **OpenAPI spec** — openapi.yaml
8. **Dockerfile + Makefile** — container and dev workflow

## Key Principles

- **Exact file paths** — always specify the full path from project root
- **Complete code** — don't write "add validation here", write the actual code
- **Verification at each step** — every task ends with a command to verify
- **DRY** — don't repeat code; if something is shared, plan the shared module first
- **YAGNI** — don't plan features not in the requirements
- **TDD** — each task follows RED-GREEN-REFACTOR (per test-driven-development skill)

## Example Plan Summary

```markdown
## Implementation Plan: Expense Portal API

**Architecture:** FastAPI + PostgreSQL (per ADR-0001, ADR-0002)
**Total tasks:** 8

1. Project scaffolding (config, pyproject.toml, __init__.py files)
2. Expense data model (SQLAlchemy + Pydantic schemas)
3. Alembic migration for expense table
4. Expense service layer (CRUD operations)
5. POST /v1/expenses endpoint (with TDD)
6. GET /v1/expenses and GET /v1/expenses/{id} endpoints
7. Health and ready endpoints
8. Dockerfile + Makefile + openapi.yaml

Proceed with this plan?
```

## After Plan Approval

Execute tasks in order. For each task:
1. Announce which task you're starting
2. Follow the test-driven-development skill (if writing business logic)
3. Verify the task is complete before moving to the next
4. If a task reveals a plan flaw, stop and discuss with the user

## Integration with Pipeline

- **@3-implementation** uses this skill to plan before coding
- The plan structure ensures TDD is applied per-task
- Verification at each step feeds into verification-before-completion
- If the plan needs revision after starting, pause and get user approval
