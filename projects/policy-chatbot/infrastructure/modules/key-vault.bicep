// key-vault.bicep — Azure Key Vault with secrets for all service connections.
// Secrets are derived from module outputs — never hardcoded.

@description('Resource name prefix')
param resourcePrefix string

@description('Azure region')
param location string

@description('Tenant ID for access policies')
param tenantId string

@description('PostgreSQL server FQDN')
param postgresServerFqdn string

@description('PostgreSQL admin login')
param postgresAdminLogin string

@secure()
@description('PostgreSQL admin password')
param postgresAdminPassword string

@description('PostgreSQL database name')
param postgresDatabaseName string

@description('Redis hostname')
param redisHostname string

@secure()
@description('Redis primary access key')
param redisPrimaryKey string

@description('Redis SSL port')
param redisPort int = 6380

@description('Storage account name')
param storageAccountName string

@description('Azure OpenAI endpoint')
param openAiEndpoint string

@description('Azure AI Search endpoint')
param searchEndpoint string

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('Entra ID tenant ID')
param entraIdTenantId string

@description('Entra ID client ID for the app registration')
param entraIdClientId string

@secure()
@description('Entra ID client secret')
param entraIdClientSecret string = ''

var keyVaultName = '${take(resourcePrefix, 20)}-kv'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 30
  }
}

// --- Secrets ---

resource secretDatabaseUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'database-url'
  properties: {
    value: 'postgresql+asyncpg://${postgresAdminLogin}:${postgresAdminPassword}@${postgresServerFqdn}:5432/${postgresDatabaseName}?ssl=require'
  }
}

resource secretRedisUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'redis-url'
  properties: {
    value: 'rediss://:${redisPrimaryKey}@${redisHostname}:${redisPort}/0'
  }
}

resource secretAppInsights 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'appinsights-connection-string'
  properties: {
    value: appInsightsConnectionString
  }
}

resource secretEntraClientSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'entra-client-secret'
  properties: {
    value: entraIdClientSecret
  }
}

output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
output databaseUrlSecretUri string = secretDatabaseUrl.properties.secretUri
output redisUrlSecretUri string = secretRedisUrl.properties.secretUri
output appInsightsSecretUri string = secretAppInsights.properties.secretUri
output entraClientSecretUri string = secretEntraClientSecret.properties.secretUri
