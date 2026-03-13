# Architecture Decision Records

ADRs document significant architectural decisions with context, options considered,
governance compliance, and consequences.

## ADR Index

| ADR | Project | Decision | Status |
|-----|---------|----------|--------|
| [ADR-0001](ADR-0001-language-selection.md) | example-ticket-app | Python + FastAPI for backend | Accepted |
| [ADR-0002](ADR-0002-data-storage.md) | example-ticket-app | PostgreSQL + built-in FTS | Accepted |
| [ADR-0003](ADR-0003-email-notifications.md) | example-ticket-app | Celery + Redis + Azure Communication Services | Accepted |

## Creating New ADRs

Use the template at `templates/design/adr-template.md`. Number sequentially
from the highest existing ADR. Every technology choice ADR MUST include a
Governance Compliance table.
