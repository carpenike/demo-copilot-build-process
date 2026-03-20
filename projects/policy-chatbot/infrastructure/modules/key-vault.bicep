// key-vault.bicep — Azure Key Vault
// Policy Chatbot — Secrets management per enterprise standards

@description('Resource name prefix for naming resources')
param resourcePrefix string

@description('Azure region for resource deployment')
param location string

@description('Environment tag (dev, staging, production)')
param environment string

@description('Azure AD tenant ID for Key Vault access policies')
param tenantId string

@description('Database connection string')
@secure()
param databaseConnectionString string

@description('Redis connection string')
@secure()
param redisConnectionString string

// KV names: alphanumeric + hyphens, 3-24 chars, globally unique
var keyVaultName = '${take(resourcePrefix, 20)}-kv'

// ─── Key Vault ─────────────────────────────────────────────────────────────────
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: environment == 'production' ? 90 : 7
    // Dev: omit enablePurgeProtection (defaults to disabled)
    // Prod: enable purge protection (irreversible)
    enablePurgeProtection: environment == 'production' ? true : null
  }
}

// ─── Secrets ───────────────────────────────────────────────────────────────────
resource dbSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'db-connection-string'
  properties: {
    value: databaseConnectionString
  }
}

resource redisSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'redis-connection-string'
  properties: {
    value: redisConnectionString
  }
}

// ─── Outputs ───────────────────────────────────────────────────────────────────
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
output keyVaultId string = keyVault.id
