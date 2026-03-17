# ADR-0008: Policy Chatbot — Compute Platform

> **Status:** Proposed
> **Date:** 2026-03-17
> **Deciders:** Platform Engineering
> **Project:** policy-chatbot

---

## Context

The policy-chatbot system consists of:
1. A REST API serving chat requests (FastAPI, I/O-bound, ~200 concurrent sessions)
2. Background workers for document ingestion and indexing (Celery tasks)
3. An admin console API (FastAPI, low traffic)

The BRD (Section 7.2) states the system "must be deployable to the existing
Kubernetes (AKS) infrastructure." However, the enterprise Cloud Service
Preference Policy mandates **Azure Container Apps (ACA) first** — AKS requires
an ADR justifying why ACA cannot meet the workload requirements.

This ADR evaluates whether ACA meets the policy-chatbot requirements or whether
AKS is necessary.

Requirements coverage: NFR-001, NFR-004, NFR-005, NFR-010, NFR-013.

---

## Decision

> We will use **Azure Container Apps (ACA)** for all policy-chatbot workloads
> because ACA meets every identified requirement and no ACA limitation has been
> found that necessitates AKS.

- **Chat API + Admin API:** ACA with HTTP ingress, autoscaling 2–10 replicas
  based on concurrent request count
- **Document indexing workers:** ACA Jobs triggered by admin console actions
  (manual re-index)
- **Celery workers:** ACA with KEDA scaling based on Redis queue depth

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Compute | ACA preferred; AKS requires ADR | ACA | ✅ |
| Container images | Docker / OCI | Docker | ✅ |
| Registry | Azure Container Registry | ACR | ✅ |
| IaC | Bicep | Bicep | ✅ |

---

## Options Considered

### Option 1: Azure Container Apps (ACA) ← Chosen

**Description:** Deploy all components as ACA apps and ACA Jobs. Use ACA's
built-in autoscaling (HTTP concurrent requests for the API, KEDA Redis scaler
for Celery workers).

**Pros:**
- Enterprise-preferred compute platform — zero governance friction
- Built-in autoscaling covers all scaling scenarios (HTTP and queue-based)
- Managed TLS, custom domains, and ingress without manual configuration
- Lower operational overhead than AKS (no node pool management, no upgrades)
- Supports Dapr for service-to-service communication if needed
- ACA revision management enables blue/green deployments
- Meets NFR-013 (3x scale to 600 concurrent conversations) via horizontal autoscale

**Cons:**
- Less control over networking topology than AKS (not required here)
- No GPU workloads (not required — LLM inference runs on Azure OpenAI Service)

### Option 2: Azure Kubernetes Service (AKS)

**Description:** Deploy to the existing AKS cluster as suggested in the BRD.

**Pros:**
- Existing infrastructure already provisioned
- Full control over networking, service mesh, resource limits
- Supports any workload type including GPU

**Cons:**
- Governance requires ADR justification — no ACA limitation has been identified
- Higher operational overhead (node pool management, Kubernetes upgrades, HPA
  configuration, ingress controller management)
- More complex deployment manifests (Helm/Kustomize) vs. simple Bicep for ACA
- Overkill for this workload — the chatbot has no AKS-specific requirements
  (no custom networking, no GPU, no service mesh, no stateful sets)

### Option 3: Azure Functions

**Description:** Serverless functions for the chat API.

**Pros:**
- Zero-scale when idle, pay per invocation
- Simplest deployment model

**Cons:**
- Cold start latency conflicts with NFR-001 (p95 < 5s response time)
- Conversation context management is awkward in stateless functions
- Celery workers don't map well to the Functions execution model
- Long-running document indexing tasks exceed typical function timeout limits

---

## Consequences

### Positive
- Fully compliant with enterprise Cloud Service Preference Policy
- Lower operational burden than AKS
- Built-in autoscaling handles both API and worker scaling patterns
- Simpler Bicep IaC than equivalent AKS manifests

### Negative / Trade-offs
- The BRD stakeholder expectation of AKS deployment must be communicated as a
  governance override. ACA provides equivalent capabilities for this workload.
- If future requirements emerge that ACA cannot handle (e.g., GPU-based local
  inference), a migration to AKS would be necessary

### Risks
- ACA scaling behavior under high concurrent LLM API calls should be load-tested
  during Development Sprint 2 to validate NFR-001
- Mitigation: configure min replicas = 2 to avoid cold start during business hours

---

## Implementation Notes

- **API app:** ACA with `minReplicas: 2`, `maxReplicas: 10`, HTTP scaling rule
  (`concurrentRequests: 20`)
- **Celery worker app:** ACA with `minReplicas: 1`, `maxReplicas: 5`, KEDA Redis
  scaling rule
- **ACA Jobs:** For bulk re-indexing tasks (FR-005, NFR-003)
- Use ACA managed identity for Azure service authentication (Key Vault, Storage,
  Azure OpenAI, AI Search)
- Bicep modules for all ACA resources

---

## References
- Governance: `governance/enterprise-standards.md` § Cloud Service Preference Policy
- Requirements: NFR-001, NFR-004, NFR-005, NFR-010, NFR-013
- Governance flag #3 from requirements: AKS vs ACA-first conflict
