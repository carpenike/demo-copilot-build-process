#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# check-prerequisites.sh — Validate Azure and GitHub prerequisites for a project
#
# Usage:
#   ./scripts/check-prerequisites.sh <project-name> <environment> [--subscription <name-or-id>] [--fix]
#
# Examples:
#   ./scripts/check-prerequisites.sh policy-chatbot dev
#   ./scripts/check-prerequisites.sh policy-chatbot dev --subscription "My Sub Name"
#   ./scripts/check-prerequisites.sh policy-chatbot dev -s 8cff5c8a-... --fix
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
FIX_MODE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fix)       FIX_MODE="--fix"; shift ;;
        --subscription|-s) SUBSCRIPTION="$2"; shift 2 ;;
        *)
            if [[ -z "$PROJECT" ]]; then PROJECT="$1"
            elif [[ -z "$ENVIRONMENT" ]]; then ENVIRONMENT="$1"
            else echo "Unknown argument: $1"; exit 1
            fi
            shift ;;
    esac
done

if [[ -z "$PROJECT" ]] || [[ -z "$ENVIRONMENT" ]]; then
    echo "Usage: $0 <project-name> <environment> [--subscription <name-or-id>] [--fix]"
    echo ""
    echo "  environment:    dev | staging | production"
    echo "  --subscription: Azure subscription name or ID (default: current az account)"
    echo "  --fix:          Auto-create missing Azure resources"
    echo ""
    echo "Examples:"
    echo "  $0 policy-chatbot dev"
    echo "  $0 policy-chatbot dev --subscription 'My Subscription Name'"
    echo "  $0 policy-chatbot dev -s 8cff5c8a-... --fix"
    exit 1
fi

if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo "Error: environment must be one of: dev, staging, production"
    exit 1
fi

REPO="carpenike/demo-copilot-build-process"
RG="rg-${PROJECT}-${ENVIRONMENT}"
LOCATION="eastus"

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
        pass "Logged in to Azure subscription: ${SUB_NAME} (${SUB_ID})"
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

if [[ -n "$ACCOUNT_INFO" ]]; then
    # Look for any ACR in the subscription
    ACR_LIST=$(az acr list --query "[].{name:name, loginServer:loginServer}" -o json 2>/dev/null)
    ACR_COUNT=$(echo "$ACR_LIST" | jq length)
    if [[ "$ACR_COUNT" -gt 0 ]]; then
        ACR_NAME=$(echo "$ACR_LIST" | jq -r '.[0].name')
        ACR_SERVER=$(echo "$ACR_LIST" | jq -r '.[0].loginServer')
        pass "ACR found: ${ACR_NAME} (${ACR_SERVER})"

        # Check if we can push
        ACR_CAN_PUSH=$(az acr check-health --name "$ACR_NAME" --yes 2>&1 || true)
        if echo "$ACR_CAN_PUSH" | grep -q "is healthy"; then
            pass "ACR '${ACR_NAME}' is healthy"
        else
            warn "ACR health check returned warnings — verify push access"
        fi
    else
        fail "No Azure Container Registry found in this subscription"
    fi
else
    skip "ACR check (not logged in)"
fi

# ─── Section 4: Azure OpenAI Service ────────────────────────────────────────

echo ""
echo -e "${BLUE}═══ Azure OpenAI Service ═══${NC}"

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
        fi

        if $HAS_EMBEDDING; then
            pass "Embedding model deployment found"
        else
            fail "No embedding model deployed — deploy text-embedding-3-large in Azure Portal"
        fi
    else
        fail "No Azure OpenAI resource found in this subscription"
    fi
else
    skip "Azure OpenAI check (not logged in)"
fi

# ─── Section 5: Entra ID App Registration ───────────────────────────────────

echo ""
echo -e "${BLUE}═══ Entra ID App Registration ═══${NC}"

if [[ -n "$ACCOUNT_INFO" ]]; then
    APP_REG=$(az ad app list --display-name "${PROJECT}" \
        --query "[].{appId:appId, displayName:displayName}" \
        -o json 2>/dev/null || echo "[]")
    APP_COUNT=$(echo "$APP_REG" | jq length)

    if [[ "$APP_COUNT" -gt 0 ]]; then
        APP_ID=$(echo "$APP_REG" | jq -r '.[0].appId')
        pass "Entra ID app registration found: ${APP_ID}"

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
    else
        fail "No Entra ID app registration found with name '${PROJECT}'"
        warn "Create one in Azure Portal → Entra ID → App registrations"
    fi
else
    skip "Entra ID check (not logged in)"
fi

# ─── Section 6: Service Principal & Federated Credentials ───────────────────

echo ""
echo -e "${BLUE}═══ Service Principal (GitHub Actions) ═══${NC}"

if [[ -n "$ACCOUNT_INFO" ]]; then
    SP_NAME="github-${PROJECT}-deploy"
    SP=$(az ad sp list --display-name "$SP_NAME" \
        --query "[].{appId:appId, displayName:displayName}" \
        -o json 2>/dev/null || echo "[]")
    SP_COUNT=$(echo "$SP" | jq length)

    if [[ "$SP_COUNT" -gt 0 ]]; then
        SP_APP_ID=$(echo "$SP" | jq -r '.[0].appId')
        pass "Service principal found: ${SP_NAME} (${SP_APP_ID})"

        # Check federated credentials
        FED_CREDS=$(az ad app federated-credential list --id "$SP_APP_ID" \
            --query "[].name" -o json 2>/dev/null || echo "[]")
        FED_COUNT=$(echo "$FED_CREDS" | jq length)

        if [[ "$FED_COUNT" -ge 2 ]]; then
            pass "Federated credentials configured (${FED_COUNT} found)"
        else
            warn "Only ${FED_COUNT} federated credential(s) — expected at least 2 (main + env)"
        fi
    else
        fail "Service principal '${SP_NAME}' not found"
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
