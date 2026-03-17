// ──────────────────────────────────────────────────────────────────────────────
// Azure Key Vault (Enterprise security standards)
// All secrets stored here — no secrets in code, config, or env vars
// ──────────────────────────────────────────────────────────────────────────────

param location string
param resourcePrefix string

@secure()
param postgresAdminPassword string

@secure()
param redisAccessKey string

@secure()
param entraClientSecret string

param databaseFqdn string
param databaseAdminLogin string
param databaseName string

var keyVaultName = '${take(resourcePrefix, 20)}-kv'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// ─── Secrets ────────────────────────────────────────────────────────────────

resource dbConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'db-connection-string'
  parent: keyVault
  properties: {
    value: 'postgresql+asyncpg://${databaseAdminLogin}:${postgresAdminPassword}@${databaseFqdn}:5432/${databaseName}?sslmode=require'
  }
}

resource redisConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'redis-connection-string'
  parent: keyVault
  properties: {
    value: 'rediss://:${redisAccessKey}@${resourcePrefix}-redis.redis.cache.windows.net:6380/0'
  }
}

resource entraClientSecretSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'entra-client-secret'
  parent: keyVault
  properties: {
    value: entraClientSecret
  }
}

output keyVaultUri string = keyVault.properties.vaultUri
output keyVaultName string = keyVault.name
