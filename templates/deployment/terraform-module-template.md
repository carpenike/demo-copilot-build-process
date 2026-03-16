# Deployment Template Reference

> **Produced by:** Deployment Agent
> **Standards:** `governance/enterprise-standards.md`

---

## Terraform Module Structure

```
infrastructure/terraform/
  main.tf           # Module calls only — no raw resources here
  variables.tf      # Input variables with descriptions and validation
  outputs.tf        # Outputs consumed by other modules or CI
  backend.tf        # Remote state configuration (Azure Storage Account)
  modules/
    acr/            # Container registry for service images
    aks-service/    # AKS deployment configuration
    rds/            # Database (if applicable)
    azure-cache/    # Cache (if applicable)
```

---

## Kubernetes Manifest Checklist

Every service deployment MUST include these manifests:

| Manifest | Purpose | Required Fields |
|----------|---------|-----------------|
| `deployment.yaml` | Pod spec + rolling update strategy | readinessProbe, livenessProbe, resources |
| `service.yaml` | ClusterIP networking | port, targetPort, selector |
| `hpa.yaml` | Horizontal Pod Autoscaler | minReplicas: 2, targetCPUUtilization: 70% |
| `pdb.yaml` | Pod Disruption Budget | minAvailable: 1 |
| `network-policy.yaml` | Default-deny + explicit allows | ingress/egress rules |
| `service-account.yaml` | Dedicated SA per service | no default SA usage |
| `external-secret.yaml` | Secrets via Azure Key Vault | secretStoreRef, target |

---

## CI Pipeline Required Stages

```yaml
jobs:
  lint:        # Static analysis + formatting check
  test:        # Unit tests with coverage report (≥ 80%)
  security:    # Microsoft Defender for Containers scan + GitHub Advanced Security dependency check
  build:       # Docker image build + push to ACR
  integration: # Integration tests against built image
```

---

## CD Pipeline Environments

```mermaid
flowchart LR
    A[main merge] --> B[dev]
    B -->|smoke tests pass| C[staging]
    C -->|manual approval| D[production]

    style B fill:#2d6a4f,color:#fff
    style C fill:#e9c46a,color:#000
    style D fill:#e76f51,color:#fff
```

---

## Resource Limits Template

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

Adjust based on load testing results. Never deploy without both requests AND limits.
