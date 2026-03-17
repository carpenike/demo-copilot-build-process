// ──────────────────────────────────────────────────────────────────────────────
// Azure Database for PostgreSQL Flexible Server (ADR-0009)
// ──────────────────────────────────────────────────────────────────────────────

param location string
param resourcePrefix string

@secure()
param administratorPassword string

param skuName string
param storageSizeGB int

var serverName = '${resourcePrefix}-${location}-pg'

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: serverName
  location: location
  sku: {
    name: skuName
    tier: contains(skuName, 'B') ? 'Burstable' : 'GeneralPurpose'
  }
  properties: {
    version: '16'
    administratorLogin: 'policychatadmin'
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: storageSizeGB
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: 14
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    // TLS 1.2+ enforced (NFR-011)
    network: {}
  }
}

// Note: require_secure_transport defaults to ON on Azure PostgreSQL Flexible Server.
// Explicitly setting it causes ServerIsBusy conflicts during deployments.

// Create the application database
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  name: 'policychatbot'
  parent: postgresServer
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Allow Azure services (Container Apps) to connect
resource firewallRule 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  name: 'AllowAzureServices'
  parent: postgresServer
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

output serverFqdn string = postgresServer.properties.fullyQualifiedDomainName
output serverName string = postgresServer.name
output databaseName string = database.name
output adminLogin string = postgresServer.properties.administratorLogin
