# Prerequisites — Policy Chatbot

> **Produced by:** @5-deployment agent
> **Date:** 2026-03-17

This document lists all Azure resources, GitHub secrets, and configuration
that must exist before the first deployment of the policy-chatbot project.

---

## 1. Azure Resources (per environment)

The Bicep templates create these automatically via `az deployment group create`.
The resource group must exist **before** running the deployment.

| Resource | Azure Service | Created By |
|----------|---------------|------------|
| Resource Group | `rg-policy-chatbot-{env}` | Manual / bootstrap script |
| ACA Environment | `policy-chatbot-{env}-env` | Bicep |
| Container App (API) | `policy-chatbot-{env}-api` | Bicep |
| Container App (Worker) | `policy-chatbot-{env}-worker` | Bicep |
| PostgreSQL | `policy-chatbot-{env}-pg` | Bicep |
| Redis Cache | `policy-chatbot-{env}-redis` | Bicep |
| Blob Storage | `policychatbot{env}` (alphanumeric) | Bicep |
| Azure AI Search | `policy-chatbot-{env}-search` | Bicep |
| Azure OpenAI | `policy-chatbot-{env}-openai` | Bicep |
| Key Vault | `policy-chatbot-{env}-kv` | Bicep |
| Log Analytics | `policy-chatbot-{env}-logs` | Bicep |
| Application Insights | `policy-chatbot-{env}-insights` | Bicep |

### Pre-existing Resources (NOT created by Bicep)

These must be created manually or by the bootstrap script before the first
deployment:

| Resource | Purpose | Notes |
|----------|---------|-------|
| **Azure Container Registry** | Docker image storage | Shared across projects; set `ACR_NAME` and `ACR_LOGIN_SERVER` secrets |
| **Resource Groups** | `rg-policy-chatbot-dev`, `-staging`, `-prod` | One per environment |
| **Service Principal** | CI/CD identity for GitHub Actions | Must have **Owner** on each resource group (for RBAC assignments) |

---

## 2. Entra ID App Registration

Create an Entra ID app registration for the policy chatbot:

1. **App name:** `policy-chatbot`
2. **Redirect URIs:** (configure per environment)
3. **App roles:** Create two roles:
   - `Employee` — default role for all users
   - `PolicyAdmin` — admin access to document management and analytics
4. **API permissions:** `User.Read` (Microsoft Graph) for employee profile lookup
5. **Expose API:** Scope `access_as_user` for admin console JWT auth

Record the **Application (client) ID** → set as `ENTRA_CLIENT_ID` secret.
Generate a **Client secret** → set as `ENTRA_CLIENT_SECRET` secret.

---

## 3. GitHub Repository Secrets

### Core Secrets (all projects)

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Service principal client ID for CI/CD |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `ACR_LOGIN_SERVER` | ACR login server (e.g., `myregistry.azurecr.io`) |
| `ACR_NAME` | ACR name (e.g., `myregistry`) |

### Project-Specific Secrets

| Secret | Description |
|--------|-------------|
| `POSTGRES_ADMIN_PASSWORD` | PostgreSQL administrator password |
| `ENTRA_CLIENT_ID` | App registration client ID for the chatbot |
| `ENTRA_CLIENT_SECRET` | App registration client secret |
| `ACA_RESOURCE_GROUP` | Dev environment resource group name |
| `ACA_RESOURCE_GROUP_STAGING` | Staging environment resource group name |
| `ACA_RESOURCE_GROUP_PROD` | Production environment resource group name |

---

## 4. GitHub Environments

Configure these environments in the repository settings with appropriate
protection rules:

| Environment | Protection Rules |
|-------------|-----------------|
| `dev` | None (auto-deploy on push to main) |
| `staging` | Required reviewers (optional) |
| `production` | Required reviewers (mandatory), deployment branch = `main` only |

---

## 5. Azure OpenAI Quota

The following model deployments are required in the Azure OpenAI resource:

| Model | Deployment Name | Minimum TPM |
|-------|----------------|-------------|
| GPT-4o | `gpt-4o` | 30K |
| GPT-4o-mini | `gpt-4o-mini` | 30K |
| text-embedding-3-large | `text-embedding-3-large` | 120K |

Ensure sufficient quota is available in the target region before deployment.

---

## 6. Bootstrap Script

To provision all Azure resources for the dev environment:

```bash
./scripts/check-prerequisites.sh policy-chatbot dev \
    --from-config projects/policy-chatbot/infrastructure/bootstrap.conf --fix
```

This will:
- Create the resource group if missing
- Check for required Azure services
- Create missing services with `--fix` flag
- Validate GitHub secrets are set
- Report any issues that need manual resolution

---

## 7. Post-Deployment Manual Steps

After the first successful deployment:

1. **Run database migrations:** The CD pipeline runs `alembic upgrade head`
   automatically. If it fails, run manually:
   ```bash
   az containerapp exec \
     --name policy-chatbot-dev-api \
     --resource-group rg-policy-chatbot-dev \
     --command "alembic upgrade head"
   ```

2. **Configure Azure Bot Service:** (manual — not created by Bicep)
   - Create a Bot Service resource in the Azure portal
   - Register the Teams channel
   - Set the messaging endpoint to `https://<api-fqdn>/api/messages`
   - Configure Direct Line for the web chat widget

3. **Assign Entra ID app roles:**
   - Assign `Employee` role to all users
   - Assign `PolicyAdmin` role to policy administrators

4. **Upload initial policy documents:** Use the admin API or admin console to
   upload the first batch of policy documents.
