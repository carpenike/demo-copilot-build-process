// storage.bicep — Azure Blob Storage for policy document files (ADR-0009).

@description('Resource name prefix (alphanumeric only for storage)')
param resourcePrefix string

@description('Azure region')
param location string

// Storage account names must be 3-24 chars, lowercase alphanumeric only
var storageAccountName = take(replace(toLower(resourcePrefix), '-', ''), 24)

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource rawContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'policy-documents'
  properties: {
    publicAccess: 'None'
  }
}

resource processedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'processed-documents'
  properties: {
    publicAccess: 'None'
  }
}

output accountName string = storageAccount.name
output accountUrl string = 'https://${storageAccount.name}.blob.${environment().suffixes.storage}'
output id string = storageAccount.id
