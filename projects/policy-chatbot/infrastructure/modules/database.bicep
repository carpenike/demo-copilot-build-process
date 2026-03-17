// database.bicep — Azure Database for PostgreSQL Flexible Server
// Standard relational store per ADR-0002 and ADR-0009.

@description('Resource name prefix')
param resourcePrefix string

@description('Azure region')
param location string

@description('Administrator login name')
param adminLogin string = 'policychatbotadmin'

@secure()
@description('Administrator password')
param adminPassword string

@description('Database name')
param databaseName string = 'policychatbot'

@description('SKU name — e.g. Standard_B1ms for dev, Standard_D2ds_v4 for prod')
param skuName string = 'Standard_B1ms'

@description('SKU tier — Burstable, GeneralPurpose, MemoryOptimized')
param skuTier string = 'Burstable'

@description('Storage size in GB')
param storageSizeGB int = 32

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: '${resourcePrefix}-pg'
  location: location
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    version: '16'
    administratorLogin: adminLogin
    administratorLoginPassword: adminPassword
    storage: {
      storageSizeGB: storageSizeGB
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: postgresServer
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Allow Azure services to connect
resource firewallAllowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: postgresServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

output serverFqdn string = postgresServer.properties.fullyQualifiedDomainName
output serverName string = postgresServer.name
output adminLogin string = adminLogin
output databaseName string = databaseName
