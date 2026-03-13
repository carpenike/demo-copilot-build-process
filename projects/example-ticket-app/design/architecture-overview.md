# Architecture Overview: Support Ticket Portal

> **Version:** 1.0
> **Date:** 2026-03-13
> **Produced by:** Design Agent
> **Related ADRs:** ADR-0001, ADR-0002, ADR-0003

---

## System Context Diagram

```mermaid
graph TB
    subgraph External
        Customer[Customer<br/>Web Browser]
        Agent[Support Agent<br/>Web Browser]
        Admin[Admin / Manager<br/>Web Browser]
        OAuth[OAuth2 Provider<br/>Microsoft Entra ID]
        ACS[Azure Communication Services<br/>Email Service]
    end

    subgraph Enterprise Boundary
        subgraph AKS Cluster
            API[Ticket API<br/>FastAPI / Python]
            Worker[Celery Worker<br/>Email Tasks]
        end

        subgraph Data Layer
            PG[(PostgreSQL<br/>Azure DB)]
            Redis[(Redis<br/>Azure Cache for Redis)]
            Blob[(Azure Blob<br/>Attachments)]
        end
    end

    Customer -->|HTTPS| API
    Agent -->|HTTPS| API
    Admin -->|HTTPS| API
    API -->|Verify JWT| OAuth
    API -->|Read/Write| PG
    API -->|Enqueue tasks| Redis
    API -->|Upload files| Blob
    Worker -->|Consume tasks| Redis
    Worker -->|Read ticket data| PG
    Worker -->|Send email| ACS
```

---

## Component Responsibilities

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| **Ticket API** | Python 3.11+ / FastAPI | REST API, auth, business logic, search |
| **Celery Worker** | Python / Celery | Async email dispatch, background processing |
| **PostgreSQL** | Azure Database for PostgreSQL | Tickets, comments, users, full-text search |
| **Redis** | Azure Cache for Redis | Celery broker + result backend |
| **Blob Storage** | Azure Blob Storage | Receipt/attachment file storage |
| **OAuth2 Provider** | Microsoft Entra ID | Authentication, JWT issuance |
| **Email Service** | Azure Communication Services | Transactional email delivery |

---

## Data Flow: Ticket Submission

```
1. Customer → API:     POST /v1/tickets (subject, description, priority)
2. API → OAuth:        Verify JWT token
3. API → PostgreSQL:   INSERT ticket row, trigger updates search_vector
4. API → Customer:     201 Created with ticket_number
```

## Data Flow: Status Change + Notification

```
1. Agent → API:        PATCH /v1/tickets/{id} (status: "in_progress")
2. API → PostgreSQL:   UPDATE ticket status, set updated_at
3. API → Redis:        Enqueue send_status_notification task
4. API → Agent:        200 OK with updated ticket
5. Worker ← Redis:     Dequeue notification task
6. Worker → PG:        Read ticket + customer email
7. Worker → ACS:        Send status change email
```

---

## Deployment Architecture

```
AKS Namespace: ticket-portal
├── Deployment: ticket-api       (2–10 replicas, HPA on CPU 70%)
├── Deployment: celery-worker    (2–5 replicas, HPA on queue depth)
├── Service: ticket-api-svc      (ClusterIP, port 8000)
├── HPA: ticket-api-hpa
├── HPA: celery-worker-hpa
├── PDB: ticket-api-pdb          (minAvailable: 1)
├── PDB: celery-worker-pdb       (minAvailable: 1)
├── NetworkPolicy: default-deny + allow ingress from Azure API Management
├── ServiceAccount: ticket-api-sa
├── ExternalSecret: db-credentials
├── ExternalSecret: redis-credentials
├── ExternalSecret: email-connection-string
└── Ingress: via Azure API Management
```

---

## Security Boundaries

| Boundary | Control |
|----------|---------|
| Internet → API | Azure API Management (WAF, rate limiting, TLS termination) |
| API → Database | VNet security group, managed identity auth |
| API → Redis | VNet security group, AUTH token |
| API → Blob Storage | Managed identity (Workload Identity), SAS URLs for client uploads |
| API → OAuth | HTTPS, JWT signature verification |
| Worker → Email | HTTPS, connection string from Azure Key Vault |
