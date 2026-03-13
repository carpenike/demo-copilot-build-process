## Summary

<!--
What does this PR do? Link to the ticket/issue.
If this implements a feature, reference the ADR: docs/adr/ADR-XXXX-*.md
-->

Closes #[issue-number]
Related ADR: [ADR-XXXX or N/A]

---

## Type of Change

- [ ] Feature (new functionality)
- [ ] Bug fix (non-breaking change that resolves an issue)
- [ ] Refactor (no behavior change)
- [ ] Test (adding or improving tests)
- [ ] Infra / deployment change
- [ ] Documentation

---

## Code Agent Checklist

> Confirm each item before requesting review.

- [ ] All tests pass locally (`make test`)
- [ ] Linter passes with zero warnings (`make lint`)
- [ ] No new TODO comments in code
- [ ] No secrets or hardcoded credentials
- [ ] `openapi.yaml` updated if endpoints were added or changed
- [ ] Dockerfile still builds successfully (`make docker-build`)
- [ ] `/health`, `/ready`, `/metrics` endpoints still functional

## Enterprise Standards Compliance

- [ ] Language used is Python or Go (no other languages introduced)
- [ ] Framework choices match `governance/enterprise-standards.md`
- [ ] No direct dependencies on prohibited packages
- [ ] Observability: structured JSON logging added for new code paths
- [ ] New environment variables documented in `.env.example`

## Test Coverage

- [ ] Unit tests added/updated for new business logic
- [ ] Integration tests added/updated for new API endpoints
- [ ] Edge cases and error paths are tested (not just happy paths)

---

## How to Test

<!-- Step-by-step instructions for the reviewer to verify this change -->

1.
2.
3.

---

## Screenshots / Logs (if applicable)

<!-- For UI changes, include before/after. For API changes, include example curl output. -->
