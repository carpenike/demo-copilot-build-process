// ──────────────────────────────────────────────────────────────────────────────
// Main Bicep orchestrator — Policy Chatbot Infrastructure
// Calls child modules for each Azure resource.
// Deploy with: az deployment group create -g <rg> -f main.bicep -p main.<env>.bicepparam
// ──────────────────────────────────────────────────────────────────────────────

targetScope = 'resourceGroup'

// ─── Parameters ─────────────────────────────────────────────────────────────

@description('Environment name (dev, staging, production)')
@allowed(['dev', 'staging', 'production'])
param environment string

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Project name used as prefix for all resources')
param projectName string = 'policy-chatbot'

@description('Container image tag (Git SHA)')
param imageTag string

@description('ACR login server (e.g., acmeacr.azurecr.io)')
param acrLoginServer string

@description('PostgreSQL administrator password — from Key Vault')
@secure()
param postgresAdminPassword string

@description('Redis access key — from Key Vault')
@secure()
param redisAccessKey string

@description('Entra ID tenant ID')
param entraTenantId string

@description('Entra ID application client ID')
param entraClientId string

@description('Entra ID client secret — from Key Vault')
@secure()
param entraClientSecret string

@description('Azure OpenAI endpoint URL')
param azureOpenAIEndpoint string

@description('Azure AI Search endpoint URL')
param azureSearchEndpoint string

@description('ServiceNow instance URL')
param servicenowInstanceUrl string

@description('CORS allowed origins (explicit list, never wildcard)')
param corsAllowedOrigins array = []

// ─── Environment-specific sizing ────────────────────────────────────────────

var envConfig = {
  dev: {
    apiMinReplicas: 1
    apiMaxReplicas: 3
    apiCpu: '0.25'
    apiMemory: '0.5Gi'
    postgresSkuName: 'Standard_B1ms'
    postgresStorageGB: 32
    redisSku: 'Basic'
    redisCapacity: 0
    searchSku: 'basic'
    searchReplicaCount: 1
  }
  staging: {
    apiMinReplicas: 2
    apiMaxReplicas: 5
    apiCpu: '0.5'
    apiMemory: '1Gi'
    postgresSkuName: 'Standard_B2s'
    postgresStorageGB: 64
    redisSku: 'Standard'
    redisCapacity: 1
    searchSku: 'standard'
    searchReplicaCount: 1
  }
  production: {
    apiMinReplicas: 2
    apiMaxReplicas: 10
    apiCpu: '0.5'
    apiMemory: '1Gi'
    postgresSkuName: 'Standard_D4s_v3'
    postgresStorageGB: 128
    redisSku: 'Standard'
    redisCapacity: 1
    searchSku: 'standard'
    searchReplicaCount: 2
  }
}

var config = envConfig[environment]
var resourcePrefix = '${projectName}-${environment}'

// ─── Module: Monitoring (deploy first — other modules reference it) ─────────

module monitoring 'modules/monitoring.bicep' = {
  name: '${resourcePrefix}-monitoring'
  params: {
    location: location
    resourcePrefix: resourcePrefix
  }
}

// ─── Module: Key Vault ──────────────────────────────────────────────────────

module keyVault 'modules/key-vault.bicep' = {
  name: '${resourcePrefix}-keyvault'
  params: {
    location: location
    resourcePrefix: resourcePrefix
    postgresAdminPassword: postgresAdminPassword
    redisAccessKey: redisAccessKey
    entraClientSecret: entraClientSecret
  }
}

// ─── Module: Database (PostgreSQL Flexible Server) ──────────────────────────

module database 'modules/database.bicep' = {
  name: '${resourcePrefix}-database'
  params: {
    location: location
    resourcePrefix: resourcePrefix
    administratorPassword: postgresAdminPassword
    skuName: config.postgresSkuName
    storageSizeGB: config.postgresStorageGB
  }
}

// ─── Module: Azure Cache for Redis ──────────────────────────────────────────

module cache 'modules/cache.bicep' = {
  name: '${resourcePrefix}-cache'
  params: {
    location: location
    resourcePrefix: resourcePrefix
    skuName: config.redisSku
    capacity: config.redisCapacity
  }
}

// ─── Module: Azure AI Search ────────────────────────────────────────────────

module search 'modules/search.bicep' = {
  name: '${resourcePrefix}-search'
  params: {
    location: location
    resourcePrefix: resourcePrefix
    skuName: config.searchSku
    replicaCount: config.searchReplicaCount
  }
}

// ─── Module: Azure Blob Storage ─────────────────────────────────────────────

module storage 'modules/storage.bicep' = {
  name: '${resourcePrefix}-storage'
  params: {
    location: location
    resourcePrefix: resourcePrefix
  }
}

// ─── Module: Container App Environment + Container App ──────────────────────

module containerApp 'modules/container-app.bicep' = {
  name: '${resourcePrefix}-container-app'
  params: {
    location: location
    resourcePrefix: resourcePrefix
    imageTag: imageTag
    acrLoginServer: acrLoginServer
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    keyVaultUri: keyVault.outputs.keyVaultUri
    searchEndpoint: azureSearchEndpoint
    openAIEndpoint: azureOpenAIEndpoint
    entraTenantId: entraTenantId
    entraClientId: entraClientId
    servicenowInstanceUrl: servicenowInstanceUrl
    blobAccountUrl: storage.outputs.blobEndpoint
    corsAllowedOrigins: corsAllowedOrigins
    minReplicas: config.apiMinReplicas
    maxReplicas: config.apiMaxReplicas
    cpuCores: config.apiCpu
    memory: config.apiMemory
  }
}

// ─── Outputs ────────────────────────────────────────────────────────────────

output containerAppFqdn string = containerApp.outputs.containerAppFqdn
output keyVaultUri string = keyVault.outputs.keyVaultUri
output databaseFqdn string = database.outputs.serverFqdn
output storageAccountName string = storage.outputs.storageAccountName
output appInsightsInstrumentationKey string = monitoring.outputs.appInsightsInstrumentationKey
