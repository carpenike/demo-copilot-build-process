# Prerequisites — Policy Chatbot Deployment

> This document lists all Azure resources, GitHub configuration, and manual
> setup steps that must be completed **before the first deployment**.

---

## 1. Azure Resource Groups

Create one resource group per environment:

```bash
az group create --name rg-policy-chatbot-dev --location eastus
az group create --name rg-policy-chatbot-staging --location eastus
az group create --name rg-policy-chatbot-prod --location eastus
```

---

## 2. Azure Container Registry (ACR)

An ACR instance must exist for storing Docker images. If a shared ACR already
exists for the organization, use it. Otherwise:

```bash
az acr create \
  --resource-group rg-shared-services \
  --name acmeacr \
  --sku Standard \
  --admin-enabled false
```

---

## 3. Azure OpenAI Service

Provision an Azure OpenAI resource in the corporate Azure tenant with:
- **GPT-4o** deployment (chat completion)
- **text-embedding-3-large** deployment (embeddings, 1536 dimensions)
- Sufficient token quota for projected query volume (Open Question #1)

```bash
az cognitiveservices account create \
  --name policy-chatbot-openai \
  --resource-group rg-policy-chatbot-prod \
  --kind OpenAI \
  --sku S0 \
  --location eastus
```

Deploy models via Azure Portal or CLI after creation.

---

## 4. Microsoft Entra ID App Registration

Register an Entra ID application for authentication (ADR-0011):

1. Go to **Azure Portal → Microsoft Entra ID → App registrations → New registration**
2. Name: `Policy Chatbot`
3. Redirect URIs:
   - `https://policy-chatbot-dev.acme.com/auth/callback` (dev)
   - `https://policy-chatbot-staging.acme.com/auth/callback` (staging)
   - `https://policy-chatbot.acme.com/auth/callback` (production)
4. API permissions: `User.Read` (Microsoft Graph)
5. Create App Roles:
   - `Employee` — assigned to all users (default)
   - `Administrator` — assigned to policy team members
6. Generate a client secret and store it in Key Vault

Record:
- **Tenant ID** → GitHub secret `ENTRA_TENANT_ID`
- **Client ID** → GitHub secret `ENTRA_CLIENT_ID`
- **Client Secret** → Azure Key Vault secret `entra-client-secret`

---

## 5. Service Principal for GitHub Actions

Create a service principal with federated credentials for OIDC-based
authentication from GitHub Actions (no stored secrets):

```bash
# Create the service principal
az ad sp create-for-rbac \
  --name "github-policy-chatbot-deploy" \
  --role Contributor \
  --scopes /subscriptions/<subscription-id> \
  --sdk-auth

# Configure federated credentials for each environment
az ad app federated-credential create \
  --id <app-object-id> \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:carpenike/demo-copilot-build-process:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

az ad app federated-credential create \
  --id <app-object-id> \
  --parameters '{
    "name": "github-env-dev",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:carpenike/demo-copilot-build-process:environment:dev",
    "audiences": ["api://AzureADTokenExchange"]
  }'

az ad app federated-credential create \
  --id <app-object-id> \
  --parameters '{
    "name": "github-env-staging",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:carpenike/demo-copilot-build-process:environment:staging",
    "audiences": ["api://AzureADTokenExchange"]
  }'

az ad app federated-credential create \
  --id <app-object-id> \
  --parameters '{
    "name": "github-env-production",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:carpenike/demo-copilot-build-process:environment:production",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

---

## 6. GitHub Repository Secrets

Configure the following secrets in **Settings → Secrets and variables → Actions**:

| Secret Name | Value | Source |
|-------------|-------|--------|
| `AZURE_CLIENT_ID` | Service principal client ID | Step 5 |
| `AZURE_TENANT_ID` | Azure AD tenant ID | Azure Portal |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | Azure Portal |
| `ACR_LOGIN_SERVER` | `acmeacr.azurecr.io` | Step 2 |
| `ACR_NAME` | `acmeacr` | Step 2 |
| `ACA_RESOURCE_GROUP_DEV` | `rg-policy-chatbot-dev` | Step 1 |
| `ACA_RESOURCE_GROUP_STAGING` | `rg-policy-chatbot-staging` | Step 1 |
| `ACA_RESOURCE_GROUP_PROD` | `rg-policy-chatbot-prod` | Step 1 |
| `POSTGRES_ADMIN_PASSWORD` | Generated secure password | Manual |
| `REDIS_ACCESS_KEY` | Redis access key (after first deploy) | Azure Portal |
| `ENTRA_TENANT_ID` | Entra ID tenant ID | Step 4 |
| `ENTRA_CLIENT_ID` | Entra ID app client ID | Step 4 |
| `ENTRA_CLIENT_SECRET` | Entra ID client secret | Step 4 |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | Step 3 |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint URL | After first deploy |
| `SERVICENOW_INSTANCE_URL` | ServiceNow instance URL | IT Service Desk |

---

## 7. GitHub Environments

Configure the following environments in **Settings → Environments**:

| Environment | Protection Rules |
|-------------|-----------------|
| `dev` | No approval required |
| `staging` | No approval required (auto-deploys after dev smoke tests pass) |
| `production` | **Required reviewers** — add Platform Engineering lead and VP Employee Experience |

---

## 8. ServiceNow Integration

Request the following from the IT Service Desk:
- A ServiceNow integration user account for the Policy Chatbot
- REST API access to the `incident` table
- Assignment group names: `HR Service Desk`, `IT Service Desk`, `Facilities Management`

Store credentials:
- `SERVICENOW_INSTANCE_URL` → GitHub secret
- ServiceNow user/password → Azure Key Vault secrets

---

## 9. DNS Configuration

Configure DNS entries for each environment:

| Environment | FQDN | Target |
|-------------|-------|--------|
| dev | `policy-chatbot-dev.acme.com` | ACA FQDN (after deploy) |
| staging | `policy-chatbot-staging.acme.com` | ACA FQDN (after deploy) |
| production | `policy-chatbot.acme.com` | Azure API Management |

---

## 10. Azure API Management (Production)

For production, configure Azure API Management as the API gateway:
- Import the OpenAPI spec (`projects/policy-chatbot/src/openapi.yaml`)
- Configure rate limiting policies
- Configure TLS termination
- Add explicit CORS policy (no wildcards)
- Route to the ACA internal ingress

---

## 11. Post-First-Deploy Steps

After the first successful deployment to each environment:

1. **Run database migrations:** Connect to the ACA container and run
   `alembic upgrade head` (or configure as an init container)
2. **Create Azure AI Search index:** The application creates the index
   on startup via `SearchService.ensure_index()`
3. **Assign Entra ID App Roles:** Assign the `Administrator` role to
   policy team members via Azure Portal → Enterprise Applications
4. **Upload initial policy documents:** Use the admin console to upload
   the initial corpus of ~140 policy documents
5. **Verify Redis connectivity:** Check that the ACA can reach Azure
   Cache for Redis and update the `REDIS_ACCESS_KEY` secret if needed

---

## Checklist

- [ ] Resource groups created (dev, staging, production)
- [ ] ACR provisioned and accessible
- [ ] Azure OpenAI resource provisioned with GPT-4o + text-embedding-3-large
- [ ] Entra ID app registration completed with App Roles
- [ ] Service principal created with federated credentials
- [ ] All GitHub secrets configured
- [ ] GitHub environments configured with approval gates
- [ ] ServiceNow integration user provisioned
- [ ] DNS entries configured
- [ ] Azure API Management configured (production)
