# ADR-0008: Compute Platform — Policy Chatbot

> **Status:** Proposed
> **Date:** 2026-03-16
> **Deciders:** Platform Engineering, VP Employee Experience
> **Project:** policy-chatbot

---

## Context

The Policy Chatbot requires a compute platform for hosting:
1. A FastAPI-based chat/admin API server (HTTP, WebSocket for streaming responses)
2. Celery background workers for document ingestion and re-indexing jobs
3. A web chat widget (static frontend)

The BRD (§7.2) states deployment to "existing Kubernetes (AKS) infrastructure."
The requirements agent flagged this as a governance conflict (GOV-003): the
enterprise Cloud Service Preference Policy mandates Azure PaaS-first, with
Azure Container Apps (ACA) as the preferred platform for HTTP APIs and
microservices. AKS is permitted only when ACA cannot meet documented
requirements, and an ADR must justify the exception.

This ADR evaluates whether ACA meets all requirements for this workload.

Related requirements: FR-010, NFR-001, NFR-004, NFR-005, NFR-013.

---

## Decision

> We will use **Azure Container Apps (ACA)** for all Policy Chatbot compute
> workloads because ACA meets every documented requirement, aligns with the
> enterprise PaaS-first policy, and reduces operational overhead compared to AKS.

- **ACA apps** for the FastAPI API server (chat, admin, health endpoints)
- **ACA Jobs** for Celery background workers (document ingestion, re-indexing)
- **Azure Static Web Apps** for the intranet chat widget frontend

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Compute (APIs) | Azure Container Apps preferred | ACA | ✅ |
| Compute (jobs) | ACA Jobs preferred | ACA Jobs | ✅ |
| Compute (static) | Azure Static Web Apps | Static Web Apps | ✅ |
| Container images | Docker / OCI-compliant | Docker | ✅ |
| IaC | Bicep | Bicep | ✅ |
| Artifact registry | Azure Container Registry | ACR | ✅ |

Reference: `governance/enterprise-standards.md`

---

## Options Considered

### Option 1: Azure Container Apps ← Chosen

**Description:** Deploy the API server as an ACA app with HTTP ingress, Celery
workers as ACA Jobs, and the web widget via Azure Static Web Apps.

**Pros:**
- Enterprise PaaS-first compliant — no exception ADR required
- Built-in autoscaling (KEDA) handles the 200→600 concurrent conversation
  scale requirement (NFR-013) without manual HPA configuration
- Built-in Dapr integration for service-to-service communication if needed
- Managed TLS termination and custom domain support
- Integrated with Azure Monitor and Application Insights out of the box
- Lower operational overhead — no cluster management, node patching, or
  control plane upgrades
- ACA supports WebSocket connections for streaming chat responses
- ACA Jobs support long-running and scheduled tasks for document ingestion (NFR-002, NFR-003)
- Message queue scaling via KEDA Azure Cache for Redis scaler for Celery workers

**Cons:**
- Less flexibility than AKS for custom networking configurations (not needed)
- No service mesh support (not needed for single-service deployment)
- Maximum 300-second timeout for HTTP requests (sufficient — chat responses
  target p95 < 5 seconds per NFR-001)

---

### Option 2: Azure Kubernetes Service (AKS)

**Description:** Deploy all workloads to the existing AKS cluster as Kubernetes
Deployments and CronJobs.

**Pros:**
- Existing AKS infrastructure is already provisioned
- Maximum flexibility for custom networking and service mesh
- Team may have existing AKS operational knowledge

**Cons:**
- **Violates enterprise PaaS-first policy** — requires an exception ADR
  justifying why ACA is insufficient
- No documented requirement for AKS-specific capabilities (custom CNI, GPU,
  service mesh, StatefulSets)
- Higher operational burden: node pool management, cluster upgrades, HPA
  configuration, ingress controller management
- BRD's mention of AKS appears to be an assumption, not a requirement

---

### Option 3: Azure App Service

**Description:** Deploy the API server as an App Service Web App.

**Pros:**
- Simple PaaS deployment model
- Governance-compliant

**Cons:**
- No native support for background Celery workers — would need a separate
  compute resource anyway
- Less autoscaling granularity than ACA
- WebSocket support is more limited than ACA

---

## Consequences

### Positive
- Full governance compliance without exception process
- Autoscaling handles 3x load growth (NFR-013) automatically
- Reduced operational overhead vs. AKS frees engineering time for feature work
- ACA Jobs provide a clean model for document ingestion background processing

### Negative / Trade-offs
- Team cannot reuse existing AKS operational runbooks (new ACA-specific runbooks needed)
- ACA has fewer escape hatches than AKS if unforeseen requirements emerge

### Risks
- ACA KEDA scaling may need tuning to handle bursty chat traffic — mitigated
  by load testing during UAT phase
- ACA Jobs have a maximum execution time of 24 hours — sufficient for full
  corpus re-indexing (target < 2 hours per NFR-003)

---

## Implementation Notes

- API server: ACA app with HTTP ingress, min replicas = 2, max replicas = 10
- Celery workers: ACA Jobs triggered by Azure Cache for Redis queue depth
- Web widget: Azure Static Web Apps with Entra ID authentication
- Container registry: Azure Container Registry (ACR)
- All infrastructure defined in Bicep
- Health endpoints: `/health` and `/ready` per enterprise security policy

---

## References
- `governance/enterprise-standards.md` — Cloud Service Preference Policy, Compute platform selection
- Requirements GOV-003 flag: AKS-first conflicts with PaaS-first policy
- Related: ADR-0007 (language), ADR-0009 (data storage)
- Related requirements: FR-010, NFR-001, NFR-004, NFR-005, NFR-013
