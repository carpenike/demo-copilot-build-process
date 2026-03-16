# Azure Bootstrap Guide

> This document lists the Azure resources and configurations that must exist
> **before** the agentic pipeline's deployment artifacts will work. The
> `@5-deployment` agent produces project-specific `PREREQUISITES.md` files, but
> the resources below are shared across all projects in this repository.

---

## 1. Resource Groups

Create one resource group per environment, plus a shared infrastructure group:

```bash
az group create --name rg-shared-infra --location eastus2
az group create --name rg-dev          --location eastus2
az group create --name rg-staging      --location eastus2
az group create --name rg-production   --location eastus2
```

> Project-specific resource groups (e.g., `rg-policy-chatbot-dev`) may also be
> created if you prefer per-project isolation. The `@5-deployment` agent will
> reference these in the generated Bicep parameter files.

---

## 2. Log Analytics Workspace

Required by Application Insights and Azure Container Apps Environments:

```bash
az monitor log-analytics workspace create \
  --resource-group rg-shared-infra \
  --workspace-name law-shared \
  --location eastus2 \
  --retention-time 90
```

Save the workspace ID — it's needed when creating ACA environments and
Application Insights instances:

```bash
LAW_ID=$(az monitor log-analytics workspace show \
  --resource-group rg-shared-infra \
  --workspace-name law-shared \
  --query id -o tsv)
```

---

## 3. Azure Container Registry (ACR)

A shared ACR for all projects:

```bash
az acr create \
  --name acmeinternalcr \
  --resource-group rg-shared-infra \
  --sku Standard \
  --admin-enabled false
```

---

## 4. Azure Container Apps Environment (Preferred Compute)

Per the Cloud Service Preference Policy, Azure Container Apps is the default
compute platform. Create one per environment:

```bash
az containerapp env create \
  --name cae-dev \
  --resource-group rg-dev \
  --location eastus2 \
  --logs-workspace-id "$LAW_ID"

az containerapp env create \
  --name cae-staging \
  --resource-group rg-staging \
  --location eastus2 \
  --logs-workspace-id "$LAW_ID"

az containerapp env create \
  --name cae-production \
  --resource-group rg-production \
  --location eastus2 \
  --logs-workspace-id "$LAW_ID"
```

> If a project requires AKS (justified by ADR), provision AKS clusters instead.
> See `governance/enterprise-standards.md` § Cloud Service Preference Policy.

---

## 5. Azure Key Vault

One Key Vault per environment. All application secrets are stored here and
injected at runtime via managed identity.

```bash
az keyvault create \
  --name kv-<project>-dev \
  --resource-group rg-dev \
  --location eastus2 \
  --enable-rbac-authorization true
```

Repeat for staging and production, adjusting the name and resource group.

---

## 6. Networking

If using ACA, networking is managed by the Container Apps Environment. If using
AKS, the following must exist:

- VNet with subnets: `snet-aks`, `snet-postgres`, `snet-redis`
- Private DNS zones: `privatelink.postgres.database.azure.com`,
  `privatelink.redis.cache.windows.net`

---

## 7. GitHub Repository Configuration

### Secrets (repository-level)

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Service principal / federated identity client ID |
| `AZURE_TENANT_ID` | Microsoft Entra ID tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `ACR_LOGIN_SERVER` | e.g., `acmeinternalcr.azurecr.io` |
| `ACR_NAME` | e.g., `acmeinternalcr` |

### Secrets (per-environment)

For each GitHub Environment (`dev`, `staging`, `production`):

| Secret | Description |
|--------|-------------|
| `KEY_VAULT_URI_<ENV>` | Key Vault URI for that environment |
| `AZURE_CLIENT_ID_<ENV>` | Workload identity for that environment |
| `ACA_ENVIRONMENT_NAME_<ENV>` | Container Apps Environment name |
| `ACA_RESOURCE_GROUP_<ENV>` | Resource group for ACA |

If using AKS instead:

| Secret | Description |
|--------|-------------|
| `AKS_RESOURCE_GROUP_<ENV>` | Resource group containing AKS cluster |
| `AKS_CLUSTER_NAME_<ENV>` | AKS cluster name |

### GitHub Environments

Create three environments in the repository settings:

1. **dev** — no approval required, auto-deploy on merge
2. **staging** — no approval required, deploys after dev smoke tests pass
3. **production** — requires manual approval from a designated reviewer

### OIDC Federated Identity

GitHub Actions uses OpenID Connect to authenticate with Azure (no stored
client secrets). Configure a federated credential on the service principal:

```bash
az ad app federated-credential create \
  --id <APP_OBJECT_ID> \
  --parameters '{
    "name": "github-actions-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<org>/<repo>:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

---

## 8. Observability (Azure Monitor)

- **Application Insights** — one instance per environment, connected to the
  shared Log Analytics workspace:
  ```bash
  az monitor app-insights component create \
    --app appi-<project>-dev \
    --location eastus2 \
    --resource-group rg-dev \
    --workspace "$LAW_ID" \
    --application-type web
  ```
- **Azure Monitor Action Groups** — configure at least two:
  - `ag-critical` — pages on-call (PagerDuty / email / Teams webhook)
  - `ag-warning` — creates ticket (ServiceNow / email)

These are referenced by the `@6-monitor` agent's Bicep alert resources.

---

## 9. CI/CD Pipeline Templates

The repository provides workflow templates in `.github/workflows/`:

| Template | Purpose |
|----------|---------|
| `ci-template.yml.template` | Python CI pipeline (lint, test, security, build, integration) |
| `ci-template-go.yml.template` | Go CI pipeline |
| `cd-template.yml.template` | Bicep deployment pipeline (dev → staging → production) |

The `@5-deployment` agent uses these templates when generating project-specific
workflows. Copy and customize for each project.

---

## 10. Project-Specific Prerequisites

Each project's `@5-deployment` agent produces a
`projects/<project>/infrastructure/PREREQUISITES.md` with additional
project-specific resources (e.g., Azure OpenAI deployments, Azure Bot Service
app registrations, specific database configurations).

Always check that document before running `az deployment group create` for a
new project.
