// main.bicep — Orchestrator for Policy Chatbot infrastructure.
// Calls child modules and sets up RBAC role assignments.
// ADRs: ADR-0008 (ACA), ADR-0009 (data storage), ADR-0010 (OpenAI), ADR-0011 (auth)

targetScope = 'resourceGroup'

// ─── Parameters ────────────────────────────────────────────────────────────────

@description('Environment name — dev, staging, production')
param environment string

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Container image tag (commit SHA)')
param imageTag string

@description('ACR login server')
param acrLoginServer string

@description('ACR name (without .azurecr.io)')
param acrName string

@secure()
@description('PostgreSQL admin password')
param postgresAdminPassword string

@description('Entra ID tenant ID')
param tenantId string = subscription().tenantId

@description('Entra ID app registration client ID')
param entraIdClientId string

@secure()
@description('Entra ID app registration client secret')
param entraIdClientSecret string = ''

@description('Optional location override for database (some regions restrict PostgreSQL)')
param databaseLocation string = ''

@description('API min replicas')
param apiMinReplicas int = 2

@description('API max replicas')
param apiMaxReplicas int = 10

@description('Worker min replicas')
param workerMinReplicas int = 1

@description('Worker max replicas')
param workerMaxReplicas int = 5

@description('PostgreSQL SKU name')
param postgresSkuName string = 'Standard_B1ms'

@description('PostgreSQL SKU tier')
param postgresSkuTier string = 'Burstable'

@description('Redis SKU name')
param redisSkuName string = 'Basic'

@description('Azure AI Search SKU')
param searchSkuName string = 'basic'

// ─── Variables ─────────────────────────────────────────────────────────────────

var resourcePrefix = 'policy-chatbot-${environment}'
var effectiveDatabaseLocation = empty(databaseLocation) ? location : databaseLocation

// RBAC role definition IDs
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

// ─── ACA Environment ───────────────────────────────────────────────────────────

resource acaEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${resourcePrefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: monitoring.outputs.logAnalyticsId
        // Shared key is retrieved at deploy time by ARM
      }
    }
  }
}

// ─── Child Modules ─────────────────────────────────────────────────────────────

module monitoring 'modules/monitoring.bicep' = {
  name: '${resourcePrefix}-monitoring'
  params: {
    resourcePrefix: resourcePrefix
    location: location
  }
}

module database 'modules/database.bicep' = {
  name: '${resourcePrefix}-database'
  params: {
    resourcePrefix: resourcePrefix
    location: effectiveDatabaseLocation
    adminPassword: postgresAdminPassword
    skuName: postgresSkuName
    skuTier: postgresSkuTier
  }
}

module cache 'modules/cache.bicep' = {
  name: '${resourcePrefix}-cache'
  params: {
    resourcePrefix: resourcePrefix
    location: location
    skuName: redisSkuName
  }
}

module storage 'modules/storage.bicep' = {
  name: '${resourcePrefix}-storage'
  params: {
    resourcePrefix: resourcePrefix
    location: location
  }
}

module search 'modules/search.bicep' = {
  name: '${resourcePrefix}-search'
  params: {
    resourcePrefix: resourcePrefix
    location: location
    skuName: searchSkuName
  }
}

module openAi 'modules/openai.bicep' = {
  name: '${resourcePrefix}-openai'
  params: {
    resourcePrefix: resourcePrefix
    location: location
  }
}

module keyVault 'modules/key-vault.bicep' = {
  name: '${resourcePrefix}-keyvault'
  params: {
    resourcePrefix: resourcePrefix
    location: location
    tenantId: tenantId
    postgresServerFqdn: database.outputs.serverFqdn
    postgresAdminLogin: database.outputs.adminLogin
    postgresAdminPassword: postgresAdminPassword
    postgresDatabaseName: database.outputs.databaseName
    redisHostname: cache.outputs.hostname
    redisPrimaryKey: cache.outputs.primaryKey
    redisPort: cache.outputs.sslPort
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    entraIdClientSecret: entraIdClientSecret
  }
}

// ─── Container Apps ────────────────────────────────────────────────────────────

module containerAppApi 'modules/container-app.bicep' = {
  name: '${resourcePrefix}-api'
  dependsOn: [keyVault, acaEnvironment]
  params: {
    resourcePrefix: resourcePrefix
    location: location
    environmentId: acaEnvironment.id
    imageTag: imageTag
    acrLoginServer: acrLoginServer
    isApi: true
    minReplicas: apiMinReplicas
    maxReplicas: apiMaxReplicas
    databaseUrlSecretUri: keyVault.outputs.databaseUrlSecretUri
    redisUrlSecretUri: keyVault.outputs.redisUrlSecretUri
    appInsightsSecretUri: keyVault.outputs.appInsightsSecretUri
    entraClientSecretUri: keyVault.outputs.entraClientSecretUri
    openAiEndpoint: openAi.outputs.openAiEndpoint
    searchEndpoint: search.outputs.searchEndpoint
    storageAccountUrl: storage.outputs.accountUrl
    tenantId: tenantId
    clientId: entraIdClientId
  }
}

module containerAppWorker 'modules/container-app.bicep' = {
  name: '${resourcePrefix}-worker'
  dependsOn: [keyVault, acaEnvironment]
  params: {
    resourcePrefix: resourcePrefix
    location: location
    environmentId: acaEnvironment.id
    imageTag: imageTag
    acrLoginServer: acrLoginServer
    isApi: false
    minReplicas: workerMinReplicas
    maxReplicas: workerMaxReplicas
    databaseUrlSecretUri: keyVault.outputs.databaseUrlSecretUri
    redisUrlSecretUri: keyVault.outputs.redisUrlSecretUri
    appInsightsSecretUri: keyVault.outputs.appInsightsSecretUri
    entraClientSecretUri: keyVault.outputs.entraClientSecretUri
    openAiEndpoint: openAi.outputs.openAiEndpoint
    searchEndpoint: search.outputs.searchEndpoint
    storageAccountUrl: storage.outputs.accountUrl
    tenantId: tenantId
    clientId: entraIdClientId
  }
}

// ─── RBAC Role Assignments ─────────────────────────────────────────────────────
// These must be inline in main.bicep (not in modules) because they reference
// outputs from multiple modules.

// --- ACR Pull (API + Worker → ACR) ---

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource acrPullApi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, '${resourcePrefix}-api', acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleId
    )
    principalId: containerAppApi.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource acrPullWorker 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, '${resourcePrefix}-worker', acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleId
    )
    principalId: containerAppWorker.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Key Vault Secrets User (API + Worker → Key Vault) ---

var keyVaultNameComputed = '${take(resourcePrefix, 20)}-kv'

resource keyVaultResource 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultNameComputed
}

resource kvSecretsApi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultNameComputed, '${resourcePrefix}-api', kvSecretsUserRoleId)
  scope: keyVaultResource
  dependsOn: [keyVault]
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      kvSecretsUserRoleId
    )
    principalId: containerAppApi.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource kvSecretsWorker 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultNameComputed, '${resourcePrefix}-worker', kvSecretsUserRoleId)
  scope: keyVaultResource
  dependsOn: [keyVault]
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      kvSecretsUserRoleId
    )
    principalId: containerAppWorker.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Azure AI Search (API + Worker → Search) ---

resource searchResource 'Microsoft.Search/searchServices@2024-03-01-preview' existing = {
  name: '${resourcePrefix}-search'
}

resource searchReaderApi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchResource.id, '${resourcePrefix}-api', searchIndexDataReaderRoleId)
  scope: searchResource
  dependsOn: [search]
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      searchIndexDataReaderRoleId
    )
    principalId: containerAppApi.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource searchContributorApi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchResource.id, '${resourcePrefix}-api', searchIndexDataContributorRoleId)
  scope: searchResource
  dependsOn: [search]
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      searchIndexDataContributorRoleId
    )
    principalId: containerAppApi.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource searchContributorWorker 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchResource.id, '${resourcePrefix}-worker', searchIndexDataContributorRoleId)
  scope: searchResource
  dependsOn: [search]
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      searchIndexDataContributorRoleId
    )
    principalId: containerAppWorker.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Azure OpenAI (API + Worker → OpenAI) ---

resource openAiResource 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: '${resourcePrefix}-openai'
}

resource openAiRoleApi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAiResource.id, '${resourcePrefix}-api', cognitiveServicesOpenAIUserRoleId)
  scope: openAiResource
  dependsOn: [openAi]
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      cognitiveServicesOpenAIUserRoleId
    )
    principalId: containerAppApi.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource openAiRoleWorker 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAiResource.id, '${resourcePrefix}-worker', cognitiveServicesOpenAIUserRoleId)
  scope: openAiResource
  dependsOn: [openAi]
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      cognitiveServicesOpenAIUserRoleId
    )
    principalId: containerAppWorker.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Azure Blob Storage (API + Worker → Storage) ---

// Compute storage name with same formula as the module — NOT from module output.
// Module outputs are runtime values and cannot be used in name/scope of
// role assignments (BCP120).
var storageAccountNameComputed = take(replace(toLower(resourcePrefix), '-', ''), 24)

resource storageResource 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountNameComputed
}

resource storageBlobApi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountNameComputed, '${resourcePrefix}-api', storageBlobDataContributorRoleId)
  scope: storageResource
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      storageBlobDataContributorRoleId
    )
    principalId: containerAppApi.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource storageBlobWorker 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountNameComputed, '${resourcePrefix}-worker', storageBlobDataContributorRoleId)
  scope: storageResource
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      storageBlobDataContributorRoleId
    )
    principalId: containerAppWorker.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// ─── Outputs ───────────────────────────────────────────────────────────────────

output apiFqdn string = containerAppApi.outputs.fqdn
output apiAppName string = containerAppApi.outputs.appName
output workerAppName string = containerAppWorker.outputs.appName
