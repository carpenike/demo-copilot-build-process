# Enterprise Engineering Standards
> Version: 2.0 | Owner: Platform Engineering | Last Updated: 2026-03

This document is the authoritative source of enterprise engineering constraints.
All agents in the pipeline MUST enforce these standards. No agent may produce
recommendations, designs, or code that violates these rules without explicit
escalation and documented exception approval.

---

## Cloud Service Preference Policy

**Azure PaaS-first.** All design and deployment decisions MUST prefer Microsoft
first-party Azure PaaS services over self-managed, third-party, or open-source
infrastructure. This applies to compute, data, networking, observability, and
every other layer of the stack.

### Decision hierarchy (in order of preference)
1. **Azure PaaS / serverless** — Azure Container Apps, Azure Functions, Azure
   App Service, Azure Database for PostgreSQL Flexible Server, Azure Cache for
   Redis, Azure Monitor, Application Insights, etc.
2. **Azure managed open-source** — Azure Managed Grafana, Azure Managed
   Prometheus (only when a PaaS equivalent does not exist).
3. **Self-managed on AKS** — Only when no PaaS or managed alternative meets the
   workload's requirements. An ADR is required justifying why PaaS was rejected.

### Compute platform selection
| Workload type | Preferred platform | Fallback (requires ADR) |
|---------------|--------------------|-------------------------|
| HTTP APIs / microservices | Azure Container Apps (ACA) | AKS |
| Background workers / jobs | ACA Jobs | AKS CronJob / Celery on ACA |
| Event-driven / short-lived | Azure Functions | ACA Jobs |
| Stateful / complex orchestration | AKS | — |
| Static web apps | Azure Static Web Apps | — |

> **AKS is NOT the default.** Use AKS only when ACA or another PaaS service
> cannot meet documented requirements (e.g., custom networking, GPU workloads,
> service mesh). The ADR must document what PaaS limitation triggered the
> decision.

---

## Language Policy

### Approved Languages
| Language | Use Case | Version Floor |
|----------|----------|---------------|
| Python   | APIs, data pipelines, ML/AI, scripting | 3.11+ |
| Go       | Services requiring high throughput, CLIs, infra tooling | 1.22+ |

### Prohibited Languages
Any language not listed above is **prohibited** for new projects. This includes
(but is not limited to) Ruby, PHP, Java, Scala, Node.js/TypeScript, Rust, and C#.

> **Exception process:** Language exceptions require VP Engineering approval and
> a completed ADR (see `templates/design/adr-template.md`) documenting the
> business justification. Approved exceptions are stored in `governance/exceptions/`.

---

## Framework Policy

### Python
| Purpose | Approved Framework |
|---------|--------------------|
| REST APIs | FastAPI |
| Background tasks / queues | Celery + Redis |
| Data pipelines | Apache Airflow |
| Testing | pytest |
| Package management | uv (preferred), pip |

### Go
| Purpose | Approved Framework |
|---------|--------------------|
| HTTP services | net/http + chi router |
| gRPC services | google.golang.org/grpc |
| CLI tools | cobra |
| Testing | testing (stdlib) + testify |

---

## Code Quality Standards

Code quality tooling is mandatory and must be configured identically across all
projects. These settings are enforced by the `@3-implementation` agent at code
generation time, by pre-commit hooks locally, and by CI pipeline lint stages.

### Python
| Tool | Purpose | Configuration |
|------|---------|---------------|
| ruff | Linting + formatting | `line-length = 100`, `target-version = "py311"` |
| mypy | Type checking | `strict = true` |
| pytest | Testing | `--cov-fail-under=80` |
| pre-commit | Local git hooks | See `.pre-commit-config.yaml` |

**Required ruff rule sets** (minimum — projects may add more):
```toml
[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "W",    # pycodestyle warnings
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "S",    # flake8-bandit (security)
    "A",    # flake8-builtins
    "C4",   # flake8-comprehensions
    "PT",   # flake8-pytest-style
    "RUF",  # ruff-specific rules
    "T20",  # flake8-print (no print statements in production code)
]
```

**Required mypy configuration:**
```toml
[tool.mypy]
python_version = "3.11"
strict = true
plugins = ["pydantic.mypy"]
```

### Go
| Tool | Purpose | Configuration |
|------|---------|---------------|
| gofmt | Formatting | stdlib default |
| golangci-lint | Linting | Config in `.golangci.yml` |
| go test | Testing | `-race -cover -coverprofile=coverage.out` |

### Pre-commit hooks
A `.pre-commit-config.yaml` is provided at the repo root. All developers must
install it (`pre-commit install`). The hooks enforce ruff, mypy, trailing
whitespace, secrets detection, and Bicep linting.

---

## Infrastructure & Deployment Policy

- **Compute platform:** Azure Container Apps (preferred) or AKS (see Cloud
  Service Preference Policy above)
- **Container images:** Docker / OCI-compliant
- **CI/CD platform:** GitHub Actions
- **Artifact registry:** Azure Container Registry (ACR)
- **IaC tooling:** Bicep (Microsoft first-party). Terraform is NOT permitted —
  Bicep is the native Azure IaC language with day-one resource support, no
  external state file, and zero licensing concerns.
- **Secrets management:** Azure Key Vault; no secrets in environment variables,
  code, or config files

---

## Security Policy

- All services must expose a `/health` and `/ready` endpoint
- TLS 1.2+ required for all service-to-service communication
- No public-facing endpoints without API gateway (Azure API Management)
- CORS origins must be explicitly listed — `allow_origins=["*"]` is prohibited
- SAST scanning (GitHub Advanced Security / CodeQL) must pass before merge
  (configured in repository settings and enforced via CI)
- All Docker base images must be sourced from the approved internal registry
- Dependency scanning (Microsoft Defender for Containers + GitHub Advanced
  Security) required in every CI pipeline

---

## Observability Requirements

All observability MUST use Azure-native services. Do NOT introduce self-managed
Prometheus, Grafana, ELK, Jaeger, or any other third-party observability stack.

Every deployed service must emit:
- **Structured logs** to stdout in JSON format (ingested by Azure Monitor /
  Log Analytics)
- **Metrics and traces** via OpenTelemetry SDK with the Azure Monitor exporter
  (`azure-monitor-opentelemetry` for Python, `azure-sdk-for-go` OTEL bridge for Go).
  Do NOT use `prometheus-fastapi-instrumentator` or standalone Prometheus
  client libraries.
- **Distributed traces** via OpenTelemetry SDK → Application Insights backend

### Alert and dashboard tooling
| Purpose | Required tool |
|---------|---------------|
| Alerting | Azure Monitor Alert Rules (Bicep `Microsoft.Insights/scheduledQueryRules` / `Microsoft.Insights/metricAlerts`) |
| Dashboards | Azure Monitor Workbooks or Azure Managed Grafana (backed by Azure Monitor data sources only) |
| Log queries | Azure Monitor Logs (KQL) — not PromQL |
| SLO tracking | Azure Monitor SLI/SLO via scheduled KQL queries |

> **No standalone Prometheus alert rules.** The `@6-monitor` agent must produce
> Azure Monitor alert definitions (as Bicep resources), not `.yaml` files
> with PromQL expressions.

---

## API Design Standards

- REST APIs must follow OpenAPI 3.1 spec; schema committed to repo as `openapi.yaml`
- Versioning: URL path versioning (`/v1/`, `/v2/`) — no header-based versioning
- Pagination: cursor-based for all list endpoints
- Error responses: RFC 7807 Problem Details format

---

## Branch & PR Policy

See `.github/branch-protection.md` for the full ruleset. Summary:
- `main` is protected; no direct pushes
- Feature branches follow `feat/<ticket-id>-short-description`
- PR requires: 2 approvals, passing CI, no unresolved comments
- Squash merge only into `main`
