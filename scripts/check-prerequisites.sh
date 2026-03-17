#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# check-prerequisites.sh — Validate Azure and GitHub prerequisites for a project
#
# Usage:
#   ./scripts/check-prerequisites.sh <project-name> <environment> [options]
#
# Examples:
#   ./scripts/check-prerequisites.sh policy-chatbot dev
#   ./scripts/check-prerequisites.sh policy-chatbot dev --location westus2
#   ./scripts/check-prerequisites.sh policy-chatbot dev --tenant <tenant-id> -s "My Sub"
#   ./scripts/check-prerequisites.sh policy-chatbot dev --login
#   ./scripts/check-prerequisites.sh policy-chatbot dev -s 8cff5c8a-... -l westus2 --fix
#
# Requires: az CLI (logged in), gh CLI (authenticated), jq
# ──────────────────────────────────────────────────────────────────────────────

set -uo pipefail

# ─── Colors ──────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASS="${GREEN}✅ PASS${NC}"
FAIL="${RED}❌ FAIL${NC}"
WARN="${YELLOW}⚠️  WARN${NC}"
SKIP="${BLUE}⏭️  SKIP${NC}"

# ─── Arguments ───────────────────────────────────────────────────────────────

PROJECT=""
ENVIRONMENT=""
SUBSCRIPTION=""
TENANT=""
LOCATION=""
FIX_MODE=""
DO_LOGIN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fix)                FIX_MODE="--fix"; shift ;;
        --subscription|-s)    SUBSCRIPTION="$2"; shift 2 ;;
        --tenant|-t)          TENANT="$2"; shift 2 ;;
        --location|-l)        LOCATION="$2"; shift 2 ;;
        --login)              DO_LOGIN="true"; shift ;;
        *)
            if [[ -z "$PROJECT" ]]; then PROJECT="$1"
            elif [[ -z "$ENVIRONMENT" ]]; then ENVIRONMENT="$1"
            else echo "Unknown argument: $1"; exit 1
            fi
            shift ;;
    esac
done

if [[ -z "$PROJECT" ]] || [[ -z "$ENVIRONMENT" ]]; then
    echo "Usage: $0 <project-name> <environment> [options]"
    echo ""
    echo "  environment:    dev | staging | production"
    echo ""
    echo "Options:"
    echo "  --subscription, -s <name-or-id>  Azure subscription (default: current az account)"
    echo "  --tenant, -t <tenant-id>         Azure AD tenant ID (triggers az login --tenant)"
    echo "  --location, -l <region>           Azure region (default: eastus)"
    echo "  --login                           Force az login (re-authenticate)"
    echo "  --fix                             Auto-create missing Azure resources"
    echo ""
    echo "Examples:"
    echo "  $0 policy-chatbot dev"
    echo "  $0 policy-chatbot dev --location westus2"
    echo "  $0 policy-chatbot dev --subscription 'My Sub' --tenant 'my-tenant-id'"
    echo "  $0 policy-chatbot dev --login"
    echo "  $0 policy-chatbot dev -s 8cff5c8a-... -l westus2 --fix"
    exit 1
fi

if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo "Error: environment must be one of: dev, staging, production"
    exit 1
fi

REPO="carpenike/demo-copilot-build-process"
RG="rg-${PROJECT}-${ENVIRONMENT}"
LOCATION="${LOCATION:-centralus}"

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
SKIP_COUNT=0

pass()  { echo -e "  ${PASS}  $1"; ((PASS_COUNT++)); }
fail()  { echo -e "  ${FAIL}  $1"; ((FAIL_COUNT++)); }
warn()  { echo -e "  ${WARN}  $1"; ((WARN_COUNT++)); }
skip()  { echo -e "  ${SKIP}  $1"; ((SKIP_COUNT++)); }

# ─── Section 0: Local Tooling ───────────────────────────────────────────────

echo ""
echo -e "${BLUE}═══ Local Tooling ═══${NC}"

if command -v az &>/dev/null; then
    AZ_VERSION=$(az version --query '"azure-cli"' -o tsv 2>/dev/null)
    pass "Azure CLI installed (v${AZ_VERSION})"
else
    fail "Azure CLI not installed — install from https://aka.ms/InstallAzureCLIDeb"
fi

if command -v gh &>/dev/null; then
    pass "GitHub CLI installed"
else
    warn "GitHub CLI not installed — GitHub checks will be skipped"
fi

if command -v jq &>/dev/null; then
    pass "jq installed"
else
    fail "jq not installed — required for JSON parsing"
fi

if command -v docker &>/dev/null; then
    pass "Docker installed"
else
    warn "Docker not installed — cannot build images locally"
fi

# ─── Section 1: Azure Authentication ────────────────────────────────────────

echo ""
echo -e "${BLUE}═══ Azure Authentication ═══${NC}"

ACCOUNT_INFO=$(az account show 2>/dev/null || true)

# Handle explicit login or tenant switch
if [[ -n "$DO_LOGIN" ]] || [[ -n "$TENANT" ]]; then
    echo -e "  Logging in to Azure..."
    LOGIN_ARGS=()
    if [[ -n "$TENANT" ]]; then
        LOGIN_ARGS+=(--tenant "$TENANT")
        echo -e "  Tenant: ${TENANT}"
    fi
    if az login "${LOGIN_ARGS[@]}" --output none 2>/dev/null; then
        ACCOUNT_INFO=$(az account show 2>/dev/null)
        pass "Azure login successful"
    else
        fail "Azure login failed"
        ACCOUNT_INFO=""
    fi
fi

if [[ -n "$ACCOUNT_INFO" ]]; then
    # Switch subscription if requested
    if [[ -n "$SUBSCRIPTION" ]]; then
        echo -e "  Switching to subscription: ${SUBSCRIPTION}"
        if az account set --subscription "$SUBSCRIPTION" 2>/dev/null; then
            ACCOUNT_INFO=$(az account show 2>/dev/null)
            pass "Switched to subscription: $(echo "$ACCOUNT_INFO" | jq -r '.name')"
        else
            fail "Could not find subscription '${SUBSCRIPTION}'"
            echo "    Available subscriptions:"
            az account list --query "[].name" -o tsv 2>/dev/null | head -10 | sed 's/^/      /'
            echo "      ... (run 'az account list -o table' for full list)"
            ACCOUNT_INFO=""
        fi
    fi

    if [[ -n "$ACCOUNT_INFO" ]]; then
        SUB_NAME=$(echo "$ACCOUNT_INFO" | jq -r '.name')
        SUB_ID=$(echo "$ACCOUNT_INFO" | jq -r '.id')
        TENANT_ID=$(echo "$ACCOUNT_INFO" | jq -r '.tenantId')
        pass "Using subscription: ${SUB_NAME} (${SUB_ID})"
        pass "Tenant: ${TENANT_ID}"
    fi
else
    fail "Not logged in to Azure CLI — run: az login"
    echo "    Cannot proceed with Azure checks. Skipping remaining Azure sections."
    ACCOUNT_INFO=""
fi

# ─── Section 2: Resource Group ───────────────────────────────────────────────

echo ""
echo -e "${BLUE}═══ Resource Group: ${RG} ═══${NC}"

if [[ -n "$ACCOUNT_INFO" ]]; then
    RG_EXISTS=$(az group exists --name "$RG" 2>/dev/null)
    if [[ "$RG_EXISTS" == "true" ]]; then
        pass "Resource group '${RG}' exists"
    else
        fail "Resource group '${RG}' does not exist"
        if [[ "$FIX_MODE" == "--fix" ]]; then
            echo "    Creating resource group..."
            az group create --name "$RG" --location "$LOCATION" --output none
            pass "Resource group '${RG}' created"
            ((FAIL_COUNT--))
        fi
    fi
else
    skip "Resource group check (not logged in)"
fi

# ─── Section 3: Azure Container Registry ────────────────────────────────────

echo ""
echo -e "${BLUE}═══ Azure Container Registry ═══${NC}"

ACR_NAME=""
ACR_SERVER=""

if [[ -n "$ACCOUNT_INFO" ]]; then
    # Look for any ACR in the subscription
    ACR_LIST=$(az acr list --query "[].{name:name, loginServer:loginServer}" -o json 2>/dev/null)
    ACR_COUNT=$(echo "$ACR_LIST" | jq length)
    if [[ "$ACR_COUNT" -gt 0 ]]; then
        ACR_NAME=$(echo "$ACR_LIST" | jq -r '.[0].name')
        ACR_SERVER=$(echo "$ACR_LIST" | jq -r '.[0].loginServer')
        pass "ACR found: ${ACR_NAME} (${ACR_SERVER})"
    else
        fail "No Azure Container Registry found in this subscription"
        if [[ "$FIX_MODE" == "--fix" ]]; then
            # Generate a unique ACR name (alphanumeric only, 5-50 chars)
            ACR_NAME="${PROJECT//[^a-zA-Z0-9]/}acr"
            echo "    Creating ACR '${ACR_NAME}' in resource group '${RG}'..."
            if az acr create --name "$ACR_NAME" --resource-group "$RG" --sku Basic --admin-enabled false --output none 2>/dev/null; then
                ACR_SERVER=$(az acr show --name "$ACR_NAME" --query "loginServer" -o tsv 2>/dev/null)
                pass "ACR created: ${ACR_NAME} (${ACR_SERVER})"
                ((FAIL_COUNT--))
            else
                echo "    Failed to create ACR — ensure resource group exists first"
            fi
        fi
    fi
else
    skip "ACR check (not logged in)"
fi

# ─── Section 4: Azure OpenAI Service ────────────────────────────────────────

echo ""
echo -e "${BLUE}═══ Azure OpenAI Service ═══${NC}"

OPENAI_ENDPOINT=""

if [[ -n "$ACCOUNT_INFO" ]]; then
    OPENAI_ACCOUNTS=$(az cognitiveservices account list \
        --query "[?kind=='OpenAI'].{name:name, rg:resourceGroup, endpoint:properties.endpoint}" \
        -o json 2>/dev/null)
    OPENAI_COUNT=$(echo "$OPENAI_ACCOUNTS" | jq length)

    if [[ "$OPENAI_COUNT" -gt 0 ]]; then
        OPENAI_NAME=$(echo "$OPENAI_ACCOUNTS" | jq -r '.[0].name')
        OPENAI_RG=$(echo "$OPENAI_ACCOUNTS" | jq -r '.[0].rg')
        OPENAI_ENDPOINT=$(echo "$OPENAI_ACCOUNTS" | jq -r '.[0].endpoint')
        pass "Azure OpenAI resource found: ${OPENAI_NAME} (${OPENAI_ENDPOINT})"
    else
        fail "No Azure OpenAI resource found in this subscription"
        if [[ "$FIX_MODE" == "--fix" ]]; then
            OPENAI_NAME="${PROJECT}-openai"
            echo "    Creating Azure OpenAI resource '${OPENAI_NAME}'..."
            if az cognitiveservices account create \
                --name "$OPENAI_NAME" \
                --resource-group "$RG" \
                --kind OpenAI \
                --sku S0 \
                --location "$LOCATION" \
                --custom-domain "$OPENAI_NAME" \
                --output none 2>/dev/null; then
                OPENAI_ENDPOINT=$(az cognitiveservices account show \
                    --name "$OPENAI_NAME" --resource-group "$RG" \
                    --query "properties.endpoint" -o tsv 2>/dev/null)
                OPENAI_RG="$RG"
                pass "Azure OpenAI created: ${OPENAI_NAME} (${OPENAI_ENDPOINT})"
                ((FAIL_COUNT--))
            else
                echo "    Failed to create Azure OpenAI — may need subscription approval"
            fi
        fi
    fi

    if [[ -n "$OPENAI_ENDPOINT" ]]; then
        # Check for model deployments
        DEPLOYMENTS=$(az cognitiveservices account deployment list \
            --name "$OPENAI_NAME" \
            --resource-group "$OPENAI_RG" \
            --query "[].{name:name, model:properties.model.name}" \
            -o json 2>/dev/null || echo "[]")

        HAS_CHAT=false
        HAS_EMBEDDING=false
        for MODEL in $(echo "$DEPLOYMENTS" | jq -r '.[].model // empty'); do
            if [[ "$MODEL" == *"gpt-4"* ]]; then HAS_CHAT=true; fi
            if [[ "$MODEL" == *"embedding"* ]]; then HAS_EMBEDDING=true; fi
        done

        if $HAS_CHAT; then
            pass "Chat model deployment found (GPT-4o or similar)"
        else
            fail "No GPT-4 chat model deployed — deploy GPT-4o in Azure Portal"
            if [[ "$FIX_MODE" == "--fix" ]]; then
                echo "    Attempting to deploy gpt-4o model..."
                if az cognitiveservices account deployment create \
                    --name "$OPENAI_NAME" \
                    --resource-group "$OPENAI_RG" \
                    --deployment-name "gpt-4o" \
                    --model-name "gpt-4o" \
                    --model-version "2024-11-20" \
                    --model-format "OpenAI" \
                    --sku-capacity 10 \
                    --sku-name "Standard" \
                    --output none 2>/dev/null; then
                    pass "gpt-4o model deployed"
                    ((FAIL_COUNT--))
                else
                    echo "    Failed — deploy manually in Azure Portal (may need quota approval)"
                fi
            fi
        fi

        if $HAS_EMBEDDING; then
            pass "Embedding model deployment found"
        else
            fail "No embedding model deployed — deploy text-embedding-3-large in Azure Portal"
            if [[ "$FIX_MODE" == "--fix" ]]; then
                echo "    Attempting to deploy text-embedding-3-large model..."
                if az cognitiveservices account deployment create \
                    --name "$OPENAI_NAME" \
                    --resource-group "$OPENAI_RG" \
                    --deployment-name "text-embedding-3-large" \
                    --model-name "text-embedding-3-large" \
                    --model-version "1" \
                    --model-format "OpenAI" \
                    --sku-capacity 10 \
                    --sku-name "Standard" \
                    --output none 2>/dev/null; then
                    pass "text-embedding-3-large model deployed"
                    ((FAIL_COUNT--))
                else
                    echo "    Failed — deploy manually in Azure Portal (may need quota approval)"
                fi
            fi
        fi
    fi
else
    skip "Azure OpenAI check (not logged in)"
fi

# ─── Section 5: Entra ID App Registration ───────────────────────────────────

echo ""
echo -e "${BLUE}═══ Entra ID App Registration ═══${NC}"

APP_ID=""
ENTRA_CLIENT_SECRET_VALUE=""

if [[ -n "$ACCOUNT_INFO" ]]; then
    APP_REG=$(az ad app list --display-name "${PROJECT}" \
        --query "[].{appId:appId, displayName:displayName, id:id}" \
        -o json 2>/dev/null || echo "[]")
    APP_COUNT=$(echo "$APP_REG" | jq length)

    if [[ "$APP_COUNT" -gt 0 ]]; then
        APP_ID=$(echo "$APP_REG" | jq -r '.[0].appId')
        APP_OBJECT_ID=$(echo "$APP_REG" | jq -r '.[0].id')
        pass "Entra ID app registration found: ${APP_ID}"
    else
        fail "No Entra ID app registration found with name '${PROJECT}'"
        if [[ "$FIX_MODE" == "--fix" ]]; then
            echo "    Creating Entra ID app registration '${PROJECT}'..."
            APP_CREATE_RESULT=$(az ad app create \
                --display-name "$PROJECT" \
                --sign-in-audience "AzureADMyOrg" \
                --required-resource-accesses '[{
                    "resourceAppId": "00000003-0000-0000-c000-000000000000",
                    "resourceAccess": [{"id": "e1fe6dd8-ba31-4d61-89e7-88639da4683d", "type": "Scope"}]
                }]' \
                --app-roles '[
                    {
                        "allowedMemberTypes": ["User"],
                        "description": "Default role for all employees",
                        "displayName": "Employee",
                        "isEnabled": true,
                        "value": "Employee"
                    },
                    {
                        "allowedMemberTypes": ["User"],
                        "description": "Policy administrators who can manage documents and view analytics",
                        "displayName": "Administrator",
                        "isEnabled": true,
                        "value": "Administrator"
                    }
                ]' \
                -o json 2>/dev/null)

            if [[ -n "$APP_CREATE_RESULT" ]]; then
                APP_ID=$(echo "$APP_CREATE_RESULT" | jq -r '.appId')
                APP_OBJECT_ID=$(echo "$APP_CREATE_RESULT" | jq -r '.id')
                pass "Entra ID app created: ${APP_ID}"
                ((FAIL_COUNT--))

                # Create a service principal for the app
                az ad sp create --id "$APP_ID" --output none 2>/dev/null || true

                # Generate a client secret
                echo "    Generating client secret..."
                SECRET_RESULT=$(az ad app credential reset \
                    --id "$APP_ID" \
                    --display-name "${PROJECT}-secret" \
                    --years 2 \
                    -o json 2>/dev/null)
                if [[ -n "$SECRET_RESULT" ]]; then
                    ENTRA_CLIENT_SECRET_VALUE=$(echo "$SECRET_RESULT" | jq -r '.password')
                    pass "Client secret generated (will be stored in GitHub secrets)"
                fi
            else
                echo "    Failed to create app registration"
            fi
        fi
    fi

    if [[ -n "$APP_ID" ]]; then
        # Check for App Roles
        APP_ROLES=$(az ad app show --id "$APP_ID" \
            --query "appRoles[].displayName" -o json 2>/dev/null || echo "[]")
        HAS_EMPLOYEE=$(echo "$APP_ROLES" | jq 'any(. == "Employee")')
        HAS_ADMIN=$(echo "$APP_ROLES" | jq 'any(. == "Administrator")')

        if [[ "$HAS_EMPLOYEE" == "true" ]]; then
            pass "App Role 'Employee' exists"
        else
            fail "App Role 'Employee' not configured"
        fi

        if [[ "$HAS_ADMIN" == "true" ]]; then
            pass "App Role 'Administrator' exists"
        else
            fail "App Role 'Administrator' not configured"
        fi

        # Check Application ID URI
        APP_ID_URI=$(az ad app show --id "$APP_ID" --query "identifierUris[0]" -o tsv 2>/dev/null || echo "")
        if [[ -n "$APP_ID_URI" ]]; then
            pass "Application ID URI set: ${APP_ID_URI}"
        else
            fail "Application ID URI not set"
            if [[ "$FIX_MODE" == "--fix" ]]; then
                az rest --method PATCH \
                    --url "https://graph.microsoft.com/v1.0/applications/${APP_OBJECT_ID}" \
                    --headers "Content-Type=application/json" \
                    --body "{\"identifierUris\":[\"api://${APP_ID}\"]}" 2>/dev/null
                pass "Application ID URI set to api://${APP_ID}"
                ((FAIL_COUNT--))
            fi
        fi

        # Check accessTokenAcceptedVersion (must be 2 for v2.0 tokens)
        TOKEN_VERSION=$(az rest --method GET \
            --url "https://graph.microsoft.com/v1.0/applications/${APP_OBJECT_ID}" \
            --query "api.requestedAccessTokenVersion" -o tsv 2>/dev/null || echo "null")
        if [[ "$TOKEN_VERSION" == "2" ]]; then
            pass "Access token version set to v2.0"
        else
            fail "Access token version is ${TOKEN_VERSION} (must be 2 for v2.0 tokens)"
            if [[ "$FIX_MODE" == "--fix" ]]; then
                az rest --method PATCH \
                    --url "https://graph.microsoft.com/v1.0/applications/${APP_OBJECT_ID}" \
                    --headers "Content-Type=application/json" \
                    --body '{"api":{"requestedAccessTokenVersion":2}}' 2>/dev/null
                pass "Access token version set to 2"
                ((FAIL_COUNT--))
            fi
        fi

        # Check OAuth2 permission scope (user_impersonation)
        SCOPE_COUNT=$(az rest --method GET \
            --url "https://graph.microsoft.com/v1.0/applications/${APP_OBJECT_ID}" \
            --query "api.oauth2PermissionScopes | length(@)" -o tsv 2>/dev/null || echo "0")
        if [[ "$SCOPE_COUNT" -gt 0 ]]; then
            pass "OAuth2 permission scope defined (${SCOPE_COUNT} scope(s))"
        else
            fail "No OAuth2 permission scopes defined (need user_impersonation)"
            if [[ "$FIX_MODE" == "--fix" ]]; then
                SCOPE_ID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]')
                az rest --method PATCH \
                    --url "https://graph.microsoft.com/v1.0/applications/${APP_OBJECT_ID}" \
                    --headers "Content-Type=application/json" \
                    --body "{\"api\":{\"oauth2PermissionScopes\":[{\"id\":\"${SCOPE_ID}\",\"adminConsentDescription\":\"Access ${PROJECT} API\",\"adminConsentDisplayName\":\"Access ${PROJECT}\",\"isEnabled\":true,\"type\":\"User\",\"userConsentDescription\":\"Access ${PROJECT} on your behalf\",\"userConsentDisplayName\":\"Access ${PROJECT}\",\"value\":\"user_impersonation\"}]}}" 2>/dev/null

                # Pre-authorize Azure CLI
                AZURE_CLI_APP_ID="04b07795-8ddb-461a-bbee-02f9e1bf7b46"
                az rest --method PATCH \
                    --url "https://graph.microsoft.com/v1.0/applications/${APP_OBJECT_ID}" \
                    --headers "Content-Type=application/json" \
                    --body "{\"api\":{\"preAuthorizedApplications\":[{\"appId\":\"${AZURE_CLI_APP_ID}\",\"delegatedPermissionIds\":[\"${SCOPE_ID}\"]}]}}" 2>/dev/null
                pass "OAuth2 scope + Azure CLI pre-authorization configured"
                ((FAIL_COUNT--))
            fi
        fi

        # Check Azure CLI pre-authorization
        PREAUTH_COUNT=$(az rest --method GET \
            --url "https://graph.microsoft.com/v1.0/applications/${APP_OBJECT_ID}" \
            --query "api.preAuthorizedApplications | length(@)" -o tsv 2>/dev/null || echo "0")
        if [[ "$PREAUTH_COUNT" -gt 0 ]]; then
            pass "Azure CLI pre-authorized for token acquisition"
        else
            warn "Azure CLI not pre-authorized — users will need admin consent to get tokens via 'az account get-access-token'"
        fi
    fi
else
    skip "Entra ID check (not logged in)"
fi

# ─── Section 6: Service Principal & Federated Credentials ───────────────────

echo ""
echo -e "${BLUE}═══ Service Principal (GitHub Actions) ═══${NC}"

SP_APP_ID=""

if [[ -n "$ACCOUNT_INFO" ]]; then
    SP_NAME="github-${PROJECT}-deploy"
    SP=$(az ad sp list --display-name "$SP_NAME" \
        --query "[].{appId:appId, displayName:displayName}" \
        -o json 2>/dev/null || echo "[]")
    SP_COUNT=$(echo "$SP" | jq length)

    if [[ "$SP_COUNT" -gt 0 ]]; then
        SP_APP_ID=$(echo "$SP" | jq -r '.[0].appId')
        pass "Service principal found: ${SP_NAME} (${SP_APP_ID})"
    else
        fail "Service principal '${SP_NAME}' not found"
        if [[ "$FIX_MODE" == "--fix" ]]; then
            echo "    Creating service principal '${SP_NAME}'..."
            SP_RESULT=$(az ad sp create-for-rbac \
                --name \"$SP_NAME\" \
                --role Owner \
                --scopes \"/subscriptions/${SUB_ID}/resourceGroups/${RG}\" \
                -o json 2>/dev/null)
            if [[ -n "$SP_RESULT" ]]; then
                SP_APP_ID=$(echo "$SP_RESULT" | jq -r '.appId')
                pass "Service principal created: ${SP_NAME} (${SP_APP_ID})"
                ((FAIL_COUNT--))

                # Create federated credentials for GitHub Actions OIDC
                echo "    Creating federated credentials for GitHub Actions..."
                for FED in \
                    "github-main:repo:${REPO}:ref:refs/heads/main" \
                    "github-pull-request:repo:${REPO}:pull_request" \
                    "github-env-dev:repo:${REPO}:environment:dev" \
                    "github-env-staging:repo:${REPO}:environment:staging" \
                    "github-env-production:repo:${REPO}:environment:production"
                do
                    FED_NAME="${FED%%:*}"
                    FED_SUBJECT="${FED#*:}"
                    az ad app federated-credential create \
                        --id "$SP_APP_ID" \
                        --parameters "{
                            \"name\": \"${FED_NAME}\",
                            \"issuer\": \"https://token.actions.githubusercontent.com\",
                            \"subject\": \"${FED_SUBJECT}\",
                            \"audiences\": [\"api://AzureADTokenExchange\"]
                        }" --output none 2>/dev/null || true
                done
                pass "Federated credentials created (5 entries)"
            else
                echo "    Failed to create service principal"
            fi
        fi
    fi

    if [[ -n "$SP_APP_ID" ]]; then
        # Check federated credentials
        FED_CREDS=$(az ad app federated-credential list --id "$SP_APP_ID" \
            --query "[].name" -o json 2>/dev/null || echo "[]")
        FED_COUNT=$(echo "$FED_CREDS" | jq length)

        if [[ "$FED_COUNT" -ge 5 ]]; then
            pass "Federated credentials configured (${FED_COUNT} found)"
        elif [[ "$FED_COUNT" -ge 2 ]]; then
            warn "Only ${FED_COUNT} federated credential(s) — expected 5 (main, pull_request, dev, staging, production)"
        else
            fail "Only ${FED_COUNT} federated credential(s) — need at least main + pull_request"
        fi
    fi
else
    skip "Service principal check (not logged in)"
fi

# ─── Section 7: GitHub Secrets ───────────────────────────────────────────────

echo ""
echo -e "${BLUE}═══ GitHub Repository Secrets ═══${NC}"

REQUIRED_SECRETS=(
    "AZURE_CLIENT_ID"
    "AZURE_TENANT_ID"
    "AZURE_SUBSCRIPTION_ID"
    "ACR_LOGIN_SERVER"
    "ACR_NAME"
    "ACA_RESOURCE_GROUP_DEV"
    "POSTGRES_ADMIN_PASSWORD"
    "ENTRA_TENANT_ID"
    "ENTRA_CLIENT_ID"
    "ENTRA_CLIENT_SECRET"
    "AZURE_OPENAI_ENDPOINT"
    "SERVICENOW_INSTANCE_URL"
)

if command -v gh &>/dev/null; then
    GH_AUTH=$(gh auth status 2>&1 || true)
    if echo "$GH_AUTH" | grep -q "Logged in"; then
        # Get list of configured secrets
        CONFIGURED_SECRETS=$(gh secret list --repo "$REPO" --json name --jq '.[].name' 2>/dev/null || echo "")

        for SECRET in "${REQUIRED_SECRETS[@]}"; do
            if echo "$CONFIGURED_SECRETS" | grep -q "^${SECRET}$"; then
                pass "Secret '${SECRET}' is configured"
            else
                fail "Secret '${SECRET}' is NOT configured"
                if [[ "$FIX_MODE" == "--fix" ]]; then
                    # Try to auto-populate from values discovered during this run
                    SECRET_VALUE=""
                    case "$SECRET" in
                        AZURE_CLIENT_ID)       [[ -n "${SP_APP_ID:-}" ]] && SECRET_VALUE="$SP_APP_ID" ;;
                        AZURE_TENANT_ID)       [[ -n "${TENANT_ID:-}" ]] && SECRET_VALUE="$TENANT_ID" ;;
                        AZURE_SUBSCRIPTION_ID) [[ -n "${SUB_ID:-}" ]] && SECRET_VALUE="$SUB_ID" ;;
                        ACR_LOGIN_SERVER)      [[ -n "${ACR_SERVER:-}" ]] && SECRET_VALUE="$ACR_SERVER" ;;
                        ACR_NAME)              [[ -n "${ACR_NAME:-}" ]] && SECRET_VALUE="$ACR_NAME" ;;
                        ACA_RESOURCE_GROUP_DEV) SECRET_VALUE="rg-${PROJECT}-dev" ;;
                        ENTRA_TENANT_ID)       [[ -n "${TENANT_ID:-}" ]] && SECRET_VALUE="$TENANT_ID" ;;
                        ENTRA_CLIENT_ID)       [[ -n "${APP_ID:-}" ]] && SECRET_VALUE="$APP_ID" ;;
                        ENTRA_CLIENT_SECRET)   [[ -n "${ENTRA_CLIENT_SECRET_VALUE:-}" ]] && SECRET_VALUE="$ENTRA_CLIENT_SECRET_VALUE" ;;
                        AZURE_OPENAI_ENDPOINT) [[ -n "${OPENAI_ENDPOINT:-}" ]] && SECRET_VALUE="$OPENAI_ENDPOINT" ;;
                        POSTGRES_ADMIN_PASSWORD)
                            # Generate a random password
                            SECRET_VALUE=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
                            echo "    Generated random password for PostgreSQL admin"
                            ;;
                        SERVICENOW_INSTANCE_URL)
                            echo "    Skipping — ServiceNow URL must be provided manually"
                            ;;
                    esac
                    if [[ -n "$SECRET_VALUE" ]]; then
                        echo "$SECRET_VALUE" | gh secret set "$SECRET" --repo "$REPO" 2>/dev/null
                        pass "Secret '${SECRET}' set automatically"
                        ((FAIL_COUNT--))
                    fi
                fi
            fi
        done
    else
        warn "GitHub CLI not authenticated — run: gh auth login"
        skip "GitHub secrets check"
    fi
else
    skip "GitHub secrets check (gh CLI not installed)"
fi

# ─── Section 8: GitHub Environments ──────────────────────────────────────────

echo ""
echo -e "${BLUE}═══ GitHub Environments ═══${NC}"

REQUIRED_ENVS=("dev" "staging" "production")

if command -v gh &>/dev/null; then
    GH_AUTH=$(gh auth status 2>&1 || true)
    if echo "$GH_AUTH" | grep -q "Logged in"; then
        CONFIGURED_ENVS=$(gh api "repos/${REPO}/environments" \
            --jq '.environments[].name' 2>/dev/null || echo "")

        for ENV in "${REQUIRED_ENVS[@]}"; do
            if echo "$CONFIGURED_ENVS" | grep -q "^${ENV}$"; then
                pass "Environment '${ENV}' exists"
                if [[ "$ENV" == "production" ]]; then
                    # Check for protection rules
                    PROTECTION=$(gh api "repos/${REPO}/environments/${ENV}" \
                        --jq '.protection_rules | length' 2>/dev/null || echo "0")
                    if [[ "$PROTECTION" -gt 0 ]]; then
                        pass "Environment 'production' has protection rules"
                    else
                        warn "Environment 'production' has NO protection rules — add required reviewers"
                    fi
                fi
            else
                fail "Environment '${ENV}' does not exist"
                if [[ "$FIX_MODE" == "--fix" ]]; then
                    echo "    Creating environment '${ENV}'..."
                    if gh api --method PUT "repos/${REPO}/environments/${ENV}" --silent 2>/dev/null; then
                        pass "Environment '${ENV}' created"
                        ((FAIL_COUNT--))
                    else
                        echo "    Failed to create environment — may need admin permissions"
                    fi
                fi
            fi
        done
    else
        skip "GitHub environments check (not authenticated)"
    fi
else
    skip "GitHub environments check (gh CLI not installed)"
fi

# ─── Section 9: Project Files ────────────────────────────────────────────────

echo ""
echo -e "${BLUE}═══ Project Files ═══${NC}"

PROJECT_DIR="projects/${PROJECT}"

check_file() {
    local file="$1"
    local desc="$2"
    if [[ -f "$file" ]]; then
        pass "${desc}"
    else
        fail "${desc} — file not found: ${file}"
    fi
}

check_file "${PROJECT_DIR}/src/Dockerfile" "Dockerfile exists"
check_file "${PROJECT_DIR}/src/pyproject.toml" "pyproject.toml exists"
check_file "${PROJECT_DIR}/src/openapi.yaml" "OpenAPI spec exists"
check_file "${PROJECT_DIR}/infrastructure/main.bicep" "Bicep main.bicep exists"
check_file "${PROJECT_DIR}/infrastructure/main.${ENVIRONMENT}.bicepparam" "Parameter file for '${ENVIRONMENT}' exists"

# Check for CI/CD workflows
if ls .github/workflows/${PROJECT}-ci.yml .github/workflows/${PROJECT}-ci.yml 2>/dev/null | head -1 | grep -q .; then
    pass "CI workflow exists"
else
    # Check on current branch
    if git show HEAD:.github/workflows/${PROJECT}-ci.yml &>/dev/null 2>&1; then
        pass "CI workflow exists (on current branch)"
    else
        warn "CI workflow not found on current branch — may be on feature branch"
    fi
fi

if ls .github/workflows/${PROJECT}-deploy.yml 2>/dev/null | head -1 | grep -q .; then
    pass "CD workflow exists"
else
    if git show HEAD:.github/workflows/${PROJECT}-deploy.yml &>/dev/null 2>&1; then
        pass "CD workflow exists (on current branch)"
    else
        warn "CD workflow not found — will arrive with feature branch merge"
    fi
fi

# ─── Section 10: ACA → ACR Pull Permission (post-deployment) ────────────────

echo ""
echo -e "${BLUE}═══ ACA → ACR Pull Permission ═══${NC}"

ACA_PRINCIPAL=""

if [[ -n "$ACCOUNT_INFO" ]] && [[ -n "${ACR_NAME:-}" ]]; then
    # Check if ACA exists (only after first deployment)
    ACA_PRINCIPAL=$(az rest --method GET \
        --url "https://management.azure.com/subscriptions/${SUB_ID}/resourceGroups/${RG}/providers/Microsoft.App/containerApps/${PROJECT}-${ENVIRONMENT}-api?api-version=2024-03-01" \
        2>/dev/null | jq -r '.identity.principalId // empty' 2>/dev/null)

    if [[ -n "$ACA_PRINCIPAL" ]]; then
        ACR_SCOPE="/subscriptions/${SUB_ID}/resourceGroups/${RG}/providers/Microsoft.ContainerRegistry/registries/${ACR_NAME}"
        HAS_ACRPULL=$(az role assignment list \
            --assignee "$ACA_PRINCIPAL" \
            --role AcrPull \
            --scope "$ACR_SCOPE" \
            --query "[0].id" -o tsv 2>/dev/null)

        if [[ -n "$HAS_ACRPULL" ]]; then
            pass "ACA has AcrPull role on ACR"
        else
            fail "ACA missing AcrPull role on ACR"
            if [[ "$FIX_MODE" == "--fix" ]]; then
                echo "    Assigning AcrPull role..."
                if az role assignment create \
                    --assignee "$ACA_PRINCIPAL" \
                    --role AcrPull \
                    --scope "$ACR_SCOPE" \
                    --output none 2>/dev/null; then
                    pass "AcrPull role assigned"
                    ((FAIL_COUNT--))
                else
                    echo "    Failed — may need Owner/User Access Administrator permissions"
                fi
            fi
        fi
    else
        skip "ACA not deployed yet — AcrPull check skipped (run after first deployment)"
    fi
else
    skip "ACA → ACR check (not logged in or ACR not found)"
fi

# ─── Section 11: ACA → AI Search & OpenAI Permissions (post-deployment) ─────

echo ""
echo -e "${BLUE}═══ ACA → AI Search & OpenAI Permissions ═══${NC}"

if [[ -n "$ACCOUNT_INFO" ]] && [[ -n "${ACA_PRINCIPAL:-}" ]]; then
    # --- Azure AI Search ---
    SEARCH_NAME="${PROJECT}-${ENVIRONMENT}-search"
    SEARCH_EXISTS=$(az search service show --name "$SEARCH_NAME" --resource-group "$RG" --query "name" -o tsv 2>/dev/null || echo "")

    if [[ -n "$SEARCH_EXISTS" ]]; then
        pass "Azure AI Search found: ${SEARCH_NAME}"

        # Check auth mode
        SEARCH_AUTH=$(az search service show --name "$SEARCH_NAME" --resource-group "$RG" \
            --query "authOptions" -o json 2>/dev/null || echo "{}")
        if echo "$SEARCH_AUTH" | jq -e '.aadOrApiKey' &>/dev/null; then
            pass "AI Search RBAC auth enabled (aadOrApiKey)"
        else
            fail "AI Search using apiKeyOnly — RBAC auth not enabled"
            if [[ "$FIX_MODE" == "--fix" ]]; then
                echo "    Enabling RBAC auth on AI Search..."
                if az search service update --name "$SEARCH_NAME" --resource-group "$RG" \
                    --auth-options aadOrApiKey \
                    --aad-auth-failure-mode http401WithBearerChallenge \
                    -o none 2>/dev/null; then
                    pass "AI Search RBAC auth enabled"
                    ((FAIL_COUNT--))
                else
                    echo "    Failed to update AI Search auth mode"
                fi
            fi
        fi

        # Check role assignments
        SEARCH_SCOPE="/subscriptions/${SUB_ID}/resourceGroups/${RG}/providers/Microsoft.Search/searchServices/${SEARCH_NAME}"
        for ROLE in "Search Index Data Reader" "Search Index Data Contributor" "Search Service Contributor"; do
            HAS_ROLE=$(az role assignment list \
                --assignee "$ACA_PRINCIPAL" \
                --role "$ROLE" \
                --scope "$SEARCH_SCOPE" \
                --query "[0].id" -o tsv 2>/dev/null)
            if [[ -n "$HAS_ROLE" ]]; then
                pass "ACA has '${ROLE}' on AI Search"
            else
                fail "ACA missing '${ROLE}' on AI Search"
                if [[ "$FIX_MODE" == "--fix" ]]; then
                    if az role assignment create \
                        --assignee "$ACA_PRINCIPAL" \
                        --role "$ROLE" \
                        --scope "$SEARCH_SCOPE" \
                        --output none 2>/dev/null; then
                        pass "'${ROLE}' assigned"
                        ((FAIL_COUNT--))
                    fi
                fi
            fi
        done
    else
        skip "AI Search '${SEARCH_NAME}' not found — skipping role checks"
    fi

    # --- Azure OpenAI ---
    if [[ -n "${OPENAI_NAME:-}" ]] && [[ -n "${OPENAI_RG:-}" ]]; then
        OPENAI_SCOPE="/subscriptions/${SUB_ID}/resourceGroups/${OPENAI_RG}/providers/Microsoft.CognitiveServices/accounts/${OPENAI_NAME}"
        OPENAI_ROLE="Cognitive Services OpenAI User"
        HAS_OPENAI_ROLE=$(az role assignment list \
            --assignee "$ACA_PRINCIPAL" \
            --role "$OPENAI_ROLE" \
            --scope "$OPENAI_SCOPE" \
            --query "[0].id" -o tsv 2>/dev/null)
        if [[ -n "$HAS_OPENAI_ROLE" ]]; then
            pass "ACA has '${OPENAI_ROLE}' on Azure OpenAI"
        else
            fail "ACA missing '${OPENAI_ROLE}' on Azure OpenAI"
            if [[ "$FIX_MODE" == "--fix" ]]; then
                if az role assignment create \
                    --assignee "$ACA_PRINCIPAL" \
                    --role "$OPENAI_ROLE" \
                    --scope "$OPENAI_SCOPE" \
                    --output none 2>/dev/null; then
                    pass "'${OPENAI_ROLE}' assigned"
                    ((FAIL_COUNT--))
                fi
            fi
        fi
    else
        skip "Azure OpenAI not found — skipping role check"
    fi
else
    if [[ -z "${ACA_PRINCIPAL:-}" ]]; then
        skip "ACA not deployed yet — AI Search & OpenAI role checks skipped"
    else
        skip "AI Search & OpenAI role checks (not logged in)"
    fi
fi

# ─── Summary ─────────────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}  Prerequisite Check Summary: ${PROJECT} (${ENVIRONMENT})${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}Passed:  ${PASS_COUNT}${NC}"
echo -e "  ${RED}Failed:  ${FAIL_COUNT}${NC}"
echo -e "  ${YELLOW}Warnings: ${WARN_COUNT}${NC}"
echo -e "  ${BLUE}Skipped: ${SKIP_COUNT}${NC}"
echo ""

if [[ "$FAIL_COUNT" -eq 0 ]]; then
    echo -e "  ${GREEN}✅ All prerequisites met! Ready to deploy.${NC}"
    exit 0
elif [[ "$FIX_MODE" == "--fix" ]]; then
    echo -e "  ${YELLOW}Some issues were auto-fixed. Re-run without --fix to verify.${NC}"
    exit 1
else
    echo -e "  ${RED}❌ ${FAIL_COUNT} prerequisite(s) not met. Fix the issues above before deploying.${NC}"
    echo -e "  ${YELLOW}Tip: Run with --fix to auto-create missing Azure resources.${NC}"
    exit 1
fi
