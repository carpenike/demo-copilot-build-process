# Platform Architecture — Acme Corporation

> Version: 1.0 | Owner: Platform Engineering | Last Updated: 2026-03

This document describes the shared platform that all services deployed through
the agentic build pipeline run on. Individual project architecture docs live in
`projects/<project>/design/architecture-overview.md`; this document covers the
cross-cutting infrastructure they all share.

---

## System Context

```mermaid
flowchart TD
    subgraph Users
        EMP[Employees]
        ADM[Admins]
        EXT[External Systems]
    end

    subgraph Edge["Edge Layer"]
        APIM[Azure API Management]
    end

    subgraph Platform["AKS Platform"]
        SVC1[expense-portal]
        SVC2[ticket-api]
        SVC3[policy-chatbot]
        FUTURE["future services..."]
    end

    subgraph Data["Data Layer"]
        PG[(Azure Database\nfor PostgreSQL)]
        REDIS[(Azure Cache\nfor Redis)]
        BLOB[(Azure Blob\nStorage)]
    end

    subgraph Observability
        PROM[Azure Monitor\nManaged Prometheus]
        LOGS[Azure Monitor\nLog Analytics]
        TRACES[Application\nInsights]
    end

    subgraph Security
        KV[Azure Key Vault]
        ENTRA[Microsoft\nEntra ID]
    end

    EMP --> APIM
    ADM --> APIM
    EXT --> APIM

    APIM --> SVC1
    APIM --> SVC2
    APIM --> SVC3

    SVC1 --> PG
    SVC1 --> REDIS
    SVC1 --> BLOB
    SVC2 --> PG
    SVC2 --> REDIS
    SVC3 --> PG

    SVC1 --> KV
    SVC2 --> KV
    SVC3 --> KV

    SVC1 -.-> PROM
    SVC1 -.-> LOGS
    SVC1 -.-> TRACES
    SVC2 -.-> PROM
    SVC2 -.-> LOGS
    SVC3 -.-> PROM
    SVC3 -.-> LOGS

    APIM --> ENTRA
```

---

## Shared Infrastructure Components

| Component | Service | Purpose |
|-----------|---------|---------|
| API Gateway | Azure API Management | TLS termination, rate limiting, auth, WAF |
| Compute | Azure Kubernetes Service (AKS) | Container orchestration for all services |
| Container Registry | Azure Container Registry (ACR) | OCI image storage, vulnerability scanning |
| Database | Azure Database for PostgreSQL Flexible Server | Managed relational data (per-service databases) |
| Cache | Azure Cache for Redis | Session state, task queues, caching |
| Object Storage | Azure Blob Storage | Receipt images, file uploads, document storage |
| Secrets | Azure Key Vault | Credentials, connection strings, API keys |
| Identity | Microsoft Entra ID | OAuth 2.0 / OIDC for user and service auth |
| DNS | Azure DNS | Service discovery and public DNS |

---

## Observability Stack

All services emit telemetry to a shared observability platform:

```mermaid
flowchart LR
    subgraph Services
        S1[Service A]
        S2[Service B]
    end

    subgraph Collection
        OTEL[OpenTelemetry\nSDK]
        PROM_EP["/metrics\nendpoint"]
        STDOUT["stdout\n(JSON logs)"]
    end

    subgraph Backend["Azure Monitor"]
        AM_PROM[Managed Prometheus]
        AM_LOGS[Log Analytics]
        AM_AI[Application Insights]
    end

    subgraph Alerting
        ALERTS[Alert Rules]
        AG[Action Groups]
        PD[PagerDuty]
    end

    S1 --> OTEL --> AM_AI
    S1 --> PROM_EP --> AM_PROM
    S1 --> STDOUT --> AM_LOGS
    S2 --> OTEL
    S2 --> PROM_EP
    S2 --> STDOUT

    AM_PROM --> ALERTS
    AM_LOGS --> ALERTS
    ALERTS --> AG --> PD
```

| Signal | Format | Collection | Backend |
|--------|--------|------------|---------|
| Logs | Structured JSON to stdout | Container log driver | Azure Monitor Log Analytics |
| Metrics | Prometheus `/metrics` endpoint | Azure Monitor managed Prometheus scrape | Grafana / Azure dashboards |
| Traces | OpenTelemetry SDK (OTLP) | OTel Collector sidecar | Application Insights |

---

## Network Architecture

```mermaid
flowchart TD
    INTERNET[Internet] --> APIM[Azure API Management\nPublic VIP]

    subgraph VNET["Corporate VNet"]
        subgraph APIM_SUBNET["APIM Subnet"]
            APIM
        end

        subgraph AKS_SUBNET["AKS Subnet"]
            AKS[AKS Cluster]
        end

        subgraph DATA_SUBNET["Data Subnet"]
            PG[(PostgreSQL)]
            REDIS[(Redis)]
        end
    end

    APIM --> AKS
    AKS --> PG
    AKS --> REDIS

    KV[Key Vault] -.->|Private Endpoint| AKS
    BLOB[Blob Storage] -.->|Private Endpoint| AKS
```

- All service-to-service communication is within the VNet (no public endpoints for data services)
- Azure API Management is the only public ingress point
- NetworkPolicy (default-deny) is enforced in every AKS namespace
- TLS 1.2+ on all connections

---

## CI/CD Platform

```mermaid
flowchart LR
    DEV[Developer] -->|push| GH[GitHub]
    GH -->|trigger| CI[GitHub Actions\nCI Pipeline]

    CI -->|lint| LINT[Static Analysis]
    CI -->|test| TEST[Unit + Integration]
    CI -->|scan| SEC[Security Scan\nCodeQL + Defender]
    CI -->|build| BUILD[Docker Build\n+ Push to ACR]

    BUILD --> CD[GitHub Actions\nCD Pipeline]

    CD -->|auto| DEV_ENV[dev]
    DEV_ENV -->|smoke pass| STG[staging]
    STG -->|manual approval| PROD[production]
```

All pipelines follow the mandatory stages defined in `governance/enterprise-standards.md`:
lint → test → security → build → integration. No stage may be skipped.

---

## Service Onboarding

When a new project goes through the agentic pipeline, it automatically gets:

1. **Namespace isolation** — dedicated AKS namespace with NetworkPolicy
2. **Dedicated service account** — no shared credentials
3. **Secrets via External Secrets Operator** — pulling from Key Vault
4. **Prometheus scrape config** — automatic via pod annotations
5. **CI/CD workflows** — generated by @5-deployment agent
6. **Alerting + runbook** — generated by @6-monitor agent

No manual infrastructure provisioning is required beyond running the pipeline.
