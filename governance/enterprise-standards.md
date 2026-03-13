# Enterprise Engineering Standards
> Version: 1.0 | Owner: Platform Engineering | Last Updated: 2026-03

This document is the authoritative source of enterprise engineering constraints.
All agents in the pipeline MUST enforce these standards. No agent may produce
recommendations, designs, or code that violates these rules without explicit
escalation and documented exception approval.

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

## Infrastructure & Deployment Policy

- **Container runtime:** Docker (OCI-compliant images only)
- **Orchestration:** Kubernetes (EKS preferred; GKE approved for GCP-native workloads)
- **CI/CD platform:** GitHub Actions
- **Artifact registry:** AWS ECR (primary), GitHub Packages (secondary)
- **IaC tooling:** Terraform (modules from the internal registry only)
- **Secrets management:** AWS Secrets Manager; no secrets in environment variables, code, or config files

---

## Security Policy

- All services must expose a `/health` and `/ready` endpoint
- TLS 1.2+ required for all service-to-service communication
- No public-facing endpoints without API gateway (AWS API Gateway or Kong)
- SAST scanning must pass before merge (see `.github/workflows/security-scan.yml`)
- All Docker base images must be sourced from the approved internal registry
- Dependency scanning (Trivy or Snyk) required in every CI pipeline

---

## Observability Requirements

Every deployed service must emit:
- **Structured logs** to stdout in JSON format (ingested by Datadog)
- **Metrics** via Prometheus-compatible `/metrics` endpoint
- **Distributed traces** via OpenTelemetry SDK (Datadog backend)

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
