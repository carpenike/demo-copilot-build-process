# Architecture Decision Records

ADRs document significant architectural decisions with context, options considered,
governance compliance, and consequences.

## ADR Index

### Platform-Wide Decisions
| ADR | Scope | Decision | Status |
|-----|-------|----------|--------|
| [ADR-0001](ADR-0001-language-selection.md) | All projects | Python + FastAPI or Go + chi as approved languages | Accepted |
| [ADR-0002](ADR-0002-data-storage.md) | All projects | Azure Database for PostgreSQL + built-in FTS | Accepted |
| [ADR-0003](ADR-0003-email-notifications.md) | All projects | Celery + Redis + Azure Communication Services | Accepted |

### Project-Level Decisions
| ADR | Project | Decision | Status |
|-----|---------|----------|--------|
| [ADR-0004](ADR-0004-expense-portal-language-selection.md) | expense-portal | Python + FastAPI for backend | Proposed |
| [ADR-0005](ADR-0005-expense-portal-data-storage.md) | expense-portal | PostgreSQL + Azure Blob Storage | Proposed |
| [ADR-0006](ADR-0006-expense-portal-authentication.md) | expense-portal | Microsoft Entra ID (OAuth 2.0 / OIDC) | Proposed |
| [ADR-0007](ADR-0007-expense-portal-ocr-service.md) | expense-portal | Azure AI Document Intelligence for OCR | Proposed |
| [ADR-0008](ADR-0008-expense-portal-async-processing.md) | expense-portal | Celery + Redis for async tasks | Proposed |

## Creating New ADRs

Use the template at `templates/design/adr-template.md`. Number sequentially
from the highest existing ADR. Every technology choice ADR MUST include a
Governance Compliance table.
