---
name: test-driven-development
description: "Use when implementing any feature or bugfix in @3-implementation — requires writing a failing test before writing implementation code. Enforces RED-GREEN-REFACTOR cycle."
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## When to Use

**Always during @3-implementation:**
- New API endpoints
- New service functions
- New business logic in `core/`
- Bug fixes

**Exceptions (confirm with user):**
- Configuration files (config.py, pyproject.toml)
- Dockerfile and Makefile
- OpenAPI spec
- Pure scaffolding (empty `__init__.py`, directory structure)

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Delete means delete

## Red-Green-Refactor Cycle

### RED — Write Failing Test

Write one minimal test showing what should happen.

```python
# Good: clear name, tests one behavior
async def test_create_expense_returns_201(
    client: AsyncClient, mock_db: AsyncMock
) -> None:
    mock_db.execute.return_value = mock_expense_result()
    response = await client.post("/v1/expenses", json=valid_expense_payload())
    assert response.status_code == 201
    assert response.json()["id"] is not None

# Bad: vague name, tests multiple things
async def test_expense_works(client: AsyncClient) -> None:
    # Tests create, read, update, delete all at once
    ...
```

**Requirements:**
- One behavior per test
- Clear descriptive name
- Real code paths (minimize mocks)

### Verify RED — Watch It Fail

**MANDATORY. Never skip.**

```bash
cd projects/<project>/src
python -m pytest ../tests/path/to/test.py::test_name -x -v
```

Confirm:
- Test fails (not errors from typos)
- Failure message is expected (e.g., "function not defined", "assert 404 != 201")
- Fails because feature is missing, not because of test bugs

**Test passes immediately?** You're testing existing behavior. Write a different test.

### GREEN — Minimal Code

Write the simplest code that makes the test pass.

```python
# Good: just enough to pass
@router.post("/v1/expenses", status_code=201)
async def create_expense(
    expense: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    result = await db.execute(insert(Expense).values(**expense.model_dump()))
    return ExpenseResponse(id=result.inserted_primary_key[0], **expense.model_dump())

# Bad: over-engineered beyond what test requires
@router.post("/v1/expenses", status_code=201)
async def create_expense(
    expense: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks,  # Not tested yet
    cache: Redis = Depends(get_cache),  # Not tested yet
) -> ExpenseResponse:
    # Caching, notifications, audit logging... none tested yet
    ...
```

Don't add features, refactor other code, or "improve" beyond the test.

### Verify GREEN — Watch It Pass

**MANDATORY.**

```bash
python -m pytest ../tests/path/to/test.py::test_name -x -v
```

Confirm:
- Test passes
- Other tests still pass (run full suite)
- No warnings or errors in output

### REFACTOR — Clean Up

After green only:
- Remove duplication
- Improve names
- Extract helpers

Keep tests green. Don't add behavior during refactoring.

### Repeat

Next failing test for next behavior.

## Practical TDD in This Pipeline

The @3-implementation agent works from ADRs and wireframe specs. Apply TDD
within this constraint:

1. **Read the wireframe-spec** — identify the endpoint or function to implement
2. **Write a test** for the expected behavior from the spec
3. **Run the test** — watch it fail
4. **Implement** — minimal code to pass
5. **Run the test** — watch it pass
6. **Next endpoint/function** — repeat

This is NOT about writing the entire test suite first. It's about writing
each test immediately before its corresponding implementation.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll write tests after" | Tests passing immediately prove nothing. |
| "Need to scaffold first" | Scaffolding is fine. But test before business logic. |
| "TDD will slow me down" | TDD is faster than debugging untested code. |
| "The @4-test agent handles testing" | @4-test writes additional tests from requirements. TDD ensures your code works as you build it. |
| "Just this one function" | One function becomes ten. Test first, every time. |

## Integration with the Pipeline

- **@3-implementation** uses this skill during code generation
- **@4-test** adds comprehensive requirement-derived tests later
- These are complementary, not redundant: TDD ensures implementation
  correctness during development; @4-test ensures requirement coverage

## Verification Checklist

Before marking implementation work complete:

- [ ] Every new endpoint/function has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] No warnings in test output

Can't check all boxes? You skipped TDD. Start over on the missed items.

## Subagent Mode

When running non-interactively (as a subagent via `runSubagent`), the
interactive RED-GREEN-REFACTOR loop can't be demonstrated step-by-step.
Adapt as follows:

- **Produce test files alongside implementation files.** For each API route
  file (`app/api/expenses.py`), produce its test file
  (`tests/test_expenses.py`) in the same task.
- **Order by dependency:** models → tests for models → services → tests
  for services → routes → tests for routes.
- **Include a test for every new endpoint** — at minimum a happy-path test
  and one error-path test per route.
- The principle still applies: the test must be written to match the
  wireframe-spec contract, not reverse-engineered from the implementation.
