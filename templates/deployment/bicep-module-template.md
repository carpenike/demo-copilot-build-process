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

### Key Vault Connection Strings

DO NOT hardcode hostnames, usernames, or database names in Key Vault secret
templates. Instead, derive them from the outputs of the modules that create
those resources:

```bicep
// WRONG — hardcoded values will drift
value: 'postgresql+asyncpg://myadmin:${password}@myserver-pg.postgres.database.azure.com:5432/mydb'

// RIGHT — derived from module outputs
value: 'postgresql+asyncpg://${database.outputs.adminLogin}:${password}@${database.outputs.serverFqdn}:5432/${database.outputs.databaseName}?ssl=require'
```

The Key Vault module must `dependsOn` any module whose outputs it references.

### ACR Pull Permission

When using ACA with managed identity to pull images from ACR, the Container
App's system-assigned identity needs the `AcrPull` role on the ACR registry.

> **Prerequisite:** The CI service principal must have **Owner** (not just
> Contributor) on the resource group to create role assignments. Scope Owner
> to the resource group — not the subscription.

Include the role assignment inline in `main.bicep`:

```bicep
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  // guid() must use compile-time values only — use resource name, not outputs
  name: guid(acr.id, '${resourcePrefix}-api', acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: containerApp.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}
```

Without this, ACA will fail with: `unable to pull image using Managed identity`.

### Key Vault Secrets User Permission

When ACA references Key Vault secrets via `keyVaultUrl` + `identity: 'system'`,
the managed identity also needs the `Key Vault Secrets User` role on the vault:

```bicep
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

// Compute KV name with same formula as the module — NOT from module output.
// Module outputs are runtime values and cannot be used in name/scope of
// role assignments (BCP120).
var keyVaultNameComputed = '${take(resourcePrefix, 20)}-kv'

resource keyVaultResource 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultNameComputed
}

resource kvSecretsRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultNameComputed, '${resourcePrefix}-api', kvSecretsUserRoleId)
  scope: keyVaultResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: containerApp.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}
```

Without this, containers will crash with: `secret "capp-<app-name>" not found`.

### Azure AI Search RBAC Authentication

Azure AI Search defaults to `apiKeyOnly` which blocks managed identity auth.
The search module MUST set `aadOrApiKey` auth and the ACA identity needs reader
roles:

```bicep
// In the search module (search.bicep):
resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: searchName
  location: location
  sku: { name: 'basic' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}
```

```bicep
// In main.bicep — role assignments for ACA → AI Search:
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'

resource searchResource 'Microsoft.Search/searchServices@2024-03-01-preview' existing = {
  name: '${resourcePrefix}-search'
}

resource searchReaderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchResource.id, '${resourcePrefix}-api', searchIndexDataReaderRoleId)
  scope: searchResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReaderRoleId)
    principalId: containerApp.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource searchContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchResource.id, '${resourcePrefix}-api', searchIndexDataContributorRoleId)
  scope: searchResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
    principalId: containerApp.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}
```

Without this, the app gets `403 Forbidden` when calling AI Search from the
container app's managed identity.

### Azure OpenAI Managed Identity Access

When the app uses `DefaultAzureCredential` to call Azure OpenAI, two things
are required:

1. **Custom subdomain** — the OpenAI resource MUST be created with
   `--custom-domain <name>` (or `customSubDomainName` in Bicep/REST). Without
   a custom subdomain, Azure rejects token auth with: *"Please provide a custom
   subdomain for token authentication, otherwise API key is required."*
2. **Role assignment** — the ACA managed identity needs the
   `Cognitive Services OpenAI User` role on the OpenAI resource:

```bicep
// In main.bicep:
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource openAiResource 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: openAiName
}

resource openAiRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAiResource.id, '${resourcePrefix}-api', cognitiveServicesOpenAIUserRoleId)
  scope: openAiResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: containerApp.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}
```

### Common Pitfalls

- **Never use placeholder values** for secrets like Redis access keys in CI
  deploy steps. Use GitHub secrets populated from the bootstrap script or manual
  `az` commands. Placeholder values propagate to Key Vault connection strings
  and cause silent connectivity failures at runtime.
- **All required Settings fields must have env vars** in the container app Bicep.
  Missing env vars cause pydantic `ValidationError` on startup — the app
  crash-loops with no clear error in multi-worker mode.
- **asyncpg uses `ssl=require`** not `sslmode=require` in connection strings.
- **Azure OpenAI `models.list()` doesn't work** — use a minimal
  `embeddings.create()` call for health checks instead.
- **Azure AI Search defaults to `apiKeyOnly`** — you MUST set `authOptions` to
  `aadOrApiKey` in the Bicep module, otherwise managed identity auth fails with
  `403 Forbidden`.
- **Database tables don't exist on first deploy.** The app will crash-loop with
  `UndefinedTableError` unless you run Alembic migrations. Always include a
  migration step in CI/CD deploy jobs.
- **FastAPI lifespan for resource init.** Use a lifespan context manager to
  call `ensure_index()` or similar initialization on startup. Without this,
  the first user request that hits an uninitialized resource (e.g., missing
  search index) returns a 500 error.
- **Entra ID token version.** App registrations default to v1.0 tokens. Set
  `requestedAccessTokenVersion: 2` in the app manifest. v1.0 tokens have
  different audience and issuer formats that cause JWT validation failures.

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
        external: false  // Set true for dev/staging (auto-assigns *.azurecontainerapps.io FQDN)
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
