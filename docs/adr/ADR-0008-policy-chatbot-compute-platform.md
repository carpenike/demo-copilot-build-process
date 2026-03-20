# ADR-0008: Policy Chatbot — Compute Platform

> **Status:** Accepted
> **Date:** 2026-03-20
> **Deciders:** Platform Engineering, HR Service Desk Manager
> **Project:** policy-chatbot

---

## Context

The Policy Chatbot needs a container hosting platform that supports auto-scaling
to handle 200–600 concurrent conversations (FR-010, NFR-013), integrates with
Azure PaaS services (Azure OpenAI, AI Search, PostgreSQL), supports managed
identity for secret-free authentication, and provides health/readiness probes.

Enterprise standards mandate Azure PaaS-first compute (`governance/enterprise-standards.md`
§ Cloud Service Preference Policy). AKS is only permitted when ACA cannot meet
documented requirements.

---

## Decision

> We will use **Azure Container Apps (ACA)** as the compute platform for the
> Policy Chatbot because it meets all workload requirements without the
> operational overhead of AKS.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Compute | ACA preferred; AKS requires ADR | Azure Container Apps | ✅ |
| Container images | Docker / OCI-compliant | Docker | ✅ |
| IaC | Bicep | Bicep | ✅ |
| Secrets | Azure Key Vault | Key Vault + Managed Identity | ✅ |
| Registry | Azure Container Registry | ACR | ✅ |

---

## Options Considered

### Option 1: Azure Container Apps (ACA) ← Chosen

**Description:** Deploy the FastAPI container on ACA with HTTP scaling rules
based on concurrent request count.

**Pros:**
- Zero Kubernetes management — no node pools, no upgrades, no RBAC config
- Built-in HTTP auto-scaling from 0 to N replicas based on concurrent requests
- Native support for managed identity (system-assigned or user-assigned)
- Built-in Dapr integration if needed for pub/sub or state management
- Ingress with automatic TLS termination
- ACA Jobs for background document ingestion tasks (FR-005, NFR-002)
- Lower cost at moderate scale — no control plane fee

**Cons:**
- Less control over networking topology compared to AKS
- No service mesh support (not needed for this workload)
- Maximum 300 replicas per revision (sufficient for 600 concurrent conversations)

---

### Option 2: Azure Kubernetes Service (AKS)

**Description:** Deploy on a managed AKS cluster with HPA-based auto-scaling.

**Pros:**
- Full Kubernetes API — maximum flexibility for networking and scheduling
- Service mesh (Istio/Linkerd) for advanced traffic management
- GPU node pools if LLM self-hosting is ever needed

**Cons:**
- Significant operational overhead — node pool management, upgrade cycles,
  cluster RBAC configuration
- Higher base cost (control plane + minimum node pool)
- Over-engineered for an HTTP API + background job workload
- Enterprise standards require an ADR justifying why ACA is insufficient —
  no such justification exists for this workload

---

### Option 3: Azure App Service

**Description:** Deploy as an App Service web app with container support.

**Pros:**
- Simple deployment model with built-in CI/CD slots
- Auto-scaling with App Service Plan

**Cons:**
- Less granular scaling controls than ACA
- No native job runner for background document ingestion
- Container support is more limited than ACA (no Dapr, no scale-to-zero)
- ACA is the enterprise-preferred platform for containerized HTTP services

---

## Consequences

### Positive
- Minimal operational burden — Platform Engineering manages ACA environment,
  not individual Kubernetes clusters
- Cost-efficient — scale-to-zero during off-hours, auto-scale during business hours
- ACA Jobs provide a clean solution for document ingestion background tasks

### Negative / Trade-offs
- Limited to ACA's networking model — if future requirements need advanced
  network policies, may need AKS migration
- Maximum 300 replicas is a hard ceiling (far above projected needs)

### Risks
- ACA feature gaps for future requirements — mitigated by ACA's rapid feature
  cadence and the fact that current requirements are well within ACA's capabilities

---

## Implementation Notes

- **API container:** ACA app with HTTP ingress, min replicas = 2, max replicas = 10
- **Ingestion worker:** ACA Job triggered by admin API or scheduled cron
- **Scaling rule:** HTTP concurrent requests — scale up at 50 concurrent
  requests per replica
- **Health probes:** `/health` (liveness) and `/ready` (readiness) endpoints
- **Managed Identity:** System-assigned identity with RBAC roles for Azure
  OpenAI, AI Search, Blob Storage, PostgreSQL, and Key Vault
- **Environment:** ACA Environment with Log Analytics workspace for log
  aggregation
- **Secrets:** Reference Azure Key Vault secrets via ACA secret references

---

## References
- [Azure Container Apps documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
- [ACA Jobs](https://learn.microsoft.com/en-us/azure/container-apps/jobs)
- Related requirements: FR-010, NFR-001, NFR-004, NFR-005, NFR-013
- Related ADRs: ADR-0007 (language/framework), ADR-0009 (data storage)
