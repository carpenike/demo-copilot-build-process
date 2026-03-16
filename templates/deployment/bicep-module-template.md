# Deployment Template Reference

> **Produced by:** Deployment Agent
> **Standards:** `governance/enterprise-standards.md`

---

## Bicep Module Structure

```
infrastructure/
  main.bicep              # Orchestrator — calls child modules
  main.dev.bicepparam     # Parameters for dev environment
  main.staging.bicepparam # Parameters for staging environment
  main.prod.bicepparam    # Parameters for production environment
  modules/
    container-app.bicep   # ACA resource definition (preferred compute)
    database.bicep        # Azure Database for PostgreSQL, etc.
    cache.bicep           # Azure Cache for Redis (if needed)
    key-vault.bicep       # Key Vault + secret references
    monitoring.bicep      # Application Insights + Log Analytics
```

> Bicep is the required IaC tool. No state file is needed — Azure Resource
> Manager is the source of truth. Deployments use `az deployment group create`
> or the `azure/arm-deploy` GitHub Action.

---

## Azure Container Apps (Preferred Compute)

ACA is the default. Only produce K8s manifests if AKS is justified by an ADR.

### Minimum Bicep configuration for a Container App:

```bicep
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${projectName}-api'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false  // Use Azure API Management for public access
        targetPort: 8000
        transport: 'http'
      }
      secrets: [
        {
          name: 'db-connection-string'
          keyVaultUrl: '${keyVaultUri}secrets/db-connection-string'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: '${acrLoginServer}/${projectName}:${imageTag}'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/ready'
                port: 8000
              }
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 2
        maxReplicas: 6
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}
```

---

## Kubernetes Manifest Checklist (AKS Fallback Only)

Only produce these if AKS is justified by an ADR:

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

Deploy with:
```bash
az deployment group create \
  --resource-group rg-<project>-<env> \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/main.<env>.bicepparam
```

Or in GitHub Actions:
```yaml
- uses: azure/arm-deploy@v2
  with:
    resourceGroupName: rg-${{ env.PROJECT }}-${{ env.ENVIRONMENT }}
    template: projects/${{ env.PROJECT }}/infrastructure/main.bicep
    parameters: projects/${{ env.PROJECT }}/infrastructure/main.${{ env.ENVIRONMENT }}.bicepparam
```

Adjust based on load testing results. Never deploy without both requests AND limits.
