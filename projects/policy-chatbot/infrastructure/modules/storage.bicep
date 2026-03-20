// storage.bicep — Azure Blob Storage
// Policy Chatbot — ADR-0009, ADR-0011: Document storage for ingestion pipeline

@description('Resource name prefix for naming resources')
param resourcePrefix string

@description('Azure region for resource deployment')
param location string

@description('Environment tag (dev, staging, production)')
param environment string

@description('Name of the blob container for policy documents')
param containerName string = 'policy-docs'

// Storage account names: lowercase, alphanumeric, 3-24 chars
var storageAccountName = take(replace('st${replace(resourcePrefix, '-', '')}', '_', ''), 24)

// ─── Storage Account ───────────────────────────────────────────────────────────
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: environment == 'production' ? 'Standard_GRS' : 'Standard_LRS'
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
  }
}

// ─── Blob Services ─────────────────────────────────────────────────────────────
resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

// ─── Container ─────────────────────────────────────────────────────────────────
resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobServices
  name: containerName
  properties: {
    publicAccess: 'None'
  }
}

// ─── Outputs ───────────────────────────────────────────────────────────────────
output storageAccountName string = storageAccount.name
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
output storageAccountId string = storageAccount.id
