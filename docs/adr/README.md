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
| [ADR-0004](ADR-0004-platform-authentication.md) | All projects | Microsoft Entra ID (OAuth 2.0 / OIDC) + application-level RBAC | Accepted |

### Project-Level Decisions
| ADR | Project | Decision | Status |
|-----|---------|----------|--------|
| [ADR-0005](ADR-0005-expense-portal-blob-storage.md) | expense-portal | Azure Blob Storage with 7-year immutable retention | Proposed |
| [ADR-0006](ADR-0006-expense-portal-ocr-service.md) | expense-portal | Azure AI Document Intelligence for receipt OCR | Proposed |

## Creating New ADRs

Use the template at `templates/design/adr-template.md`. Number sequentially
from the highest existing ADR. Every technology choice ADR MUST include a
Governance Compliance table.
