// main.bicep — Orchestrator for Policy Chatbot infrastructure
// Calls child modules for each Azure resource.
// Deploy with: az deployment group create --template-file main.bicep --parameters main.<env>.bicepparam

@description('Resource name prefix (e.g., policy-chatbot-dev)')
param resourcePrefix string

@description('Azure region for resource deployment')
param location string = resourceGroup().location

@description('Environment tag (dev, staging, production)')
param environment string

@description('Container image tag (git SHA)')
param imageTag string

@description('ACR login server (e.g., myacr.azurecr.io)')
param acrLoginServer string

@description('Existing ACR name for role assignments')
param acrName string

@description('Azure AD tenant ID')
param tenantId string = subscription().tenantId

@secure()
@description('PostgreSQL admin password')
param postgresAdminPassword string

@description('PostgreSQL SKU name')
param postgresSkuName string = 'Standard_B1ms'

@description('PostgreSQL SKU tier')
param postgresSkuTier string = 'Burstable'

@description('Location override for database (if main region is restricted)')
param databaseLocation string = ''

@description('Entra ID tenant ID for app authentication')
param entraTenantId string = ''

@description('Entra ID client ID (app registration)')
param entraClientId string = ''

@description('Entra ID authority URL')
param entraAuthority string = ''

@description('Allowed CORS origins')
param allowedOrigins string = 'https://intranet.acme.com'

// ─── Monitoring (deploy first — others depend on Log Analytics) ────────────────
module monitoring 'modules/monitoring.bicep' = {
  name: '${resourcePrefix}-monitoring'
  params: {
    resourcePrefix: resourcePrefix
    location: location
    environment: environment
  }
}

// ─── Database ──────────────────────────────────────────────────────────────────
module database 'modules/database.bicep' = {
  name: '${resourcePrefix}-database'
  params: {
    resourcePrefix: resourcePrefix
    location: databaseLocation != '' ? databaseLocation : location
    environment: environment
    adminPassword: postgresAdminPassword
    skuName: postgresSkuName
    skuTier: postgresSkuTier
  }
}

// ─── Cache (Redis) ─────────────────────────────────────────────────────────────
module cache 'modules/cache.bicep' = {
  name: '${resourcePrefix}-cache'
  params: {
    resourcePrefix: resourcePrefix
    location: location
    environment: environment
  }
}

// ─── Blob Storage ──────────────────────────────────────────────────────────────
module storage 'modules/storage.bicep' = {
  name: '${resourcePrefix}-storage'
  params: {
    resourcePrefix: resourcePrefix
    location: location
    environment: environment
  }
}

// ─── Azure AI Search ───────────────────────────────────────────────────────────
module search 'modules/search.bicep' = {
  name: '${resourcePrefix}-search'
  params: {
    resourcePrefix: resourcePrefix
    location: location
    environment: environment
  }
}

// ─── Azure OpenAI ──────────────────────────────────────────────────────────────
module openai 'modules/openai.bicep' = {
  name: '${resourcePrefix}-openai'
  params: {
    resourcePrefix: resourcePrefix
    location: location
  }
}

// ─── Key Vault ─────────────────────────────────────────────────────────────────
// Connection strings derived from module outputs — no hardcoded values.
module keyVault 'modules/key-vault.bicep' = {
  name: '${resourcePrefix}-keyvault'
  params: {
    resourcePrefix: resourcePrefix
    location: location
    environment: environment
    tenantId: tenantId
    databaseConnectionString: 'postgresql+asyncpg://${database.outputs.adminLogin}:${postgresAdminPassword}@${database.outputs.serverFqdn}:5432/${database.outputs.databaseName}?ssl=require'
    redisConnectionString: 'rediss://:${cache.outputs.redisPrimaryKey}@${cache.outputs.redisHostName}:${cache.outputs.redisPort}/0'
  }
}

// ─── ACA Managed Environment ──────────────────────────────────────────────────
resource acaEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${resourcePrefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: monitoring.outputs.logAnalyticsCustomerId
        sharedKey: monitoring.outputs.logAnalyticsSharedKey
      }
    }
  }
}

// ─── Container App (API) ───────────────────────────────────────────────────────
module containerApp 'modules/container-app.bicep' = {
  name: '${resourcePrefix}-containerapp'
  params: {
    resourcePrefix: resourcePrefix
    location: location
    environment: environment
    imageTag: imageTag
    acrLoginServer: acrLoginServer
    managedEnvironmentId: acaEnvironment.id
    keyVaultUri: keyVault.outputs.keyVaultUri
    blobAccountUrl: storage.outputs.blobEndpoint
    searchEndpoint: search.outputs.searchEndpoint
    openAiEndpoint: openai.outputs.openAiEndpoint
    entraTenantId: entraTenantId
    entraClientId: entraClientId
    entraAuthority: entraAuthority
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    allowedOrigins: allowedOrigins
  }
}

// ─── RBAC Role Assignments ─────────────────────────────────────────────────────
// These must be inline in main.bicep because role assignment name/scope
// cannot reference module outputs (BCP120). Compute resource names using
// the same formula as the child modules.

// --- ACR Pull ---
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, '${resourcePrefix}-api', acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: containerApp.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Key Vault Secrets User ---
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
var keyVaultNameComputed = '${take(resourcePrefix, 20)}-kv'

resource keyVaultResource 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultNameComputed
}

resource kvSecretsRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultResource.id, '${resourcePrefix}-api', kvSecretsUserRoleId)
  scope: keyVaultResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: containerApp.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Azure AI Search: Index Data Reader + Index Data Contributor + Service Contributor ---
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'

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

resource searchServiceContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchResource.id, '${resourcePrefix}-api', searchServiceContributorRoleId)
  scope: searchResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
    principalId: containerApp.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Azure OpenAI: Cognitive Services OpenAI User ---
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource openAiResource 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: '${resourcePrefix}-openai'
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

// --- Azure Blob Storage: Storage Blob Data Contributor ---
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
// Compute storage account name with same formula as storage module (no module output refs in name/scope)
var storageAccountNameComputed = take(replace('st${replace(resourcePrefix, '-', '')}', '_', ''), 24)

resource storageResource 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountNameComputed
}

resource storageBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountNameComputed, '${resourcePrefix}-api', storageBlobDataContributorRoleId)
  scope: storageResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: containerApp.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// ─── Outputs ───────────────────────────────────────────────────────────────────
output containerAppFqdn string = containerApp.outputs.fqdn
output containerAppName string = containerApp.outputs.appName
output keyVaultUri string = keyVault.outputs.keyVaultUri
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
