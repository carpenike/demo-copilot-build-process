// search.bicep — Azure AI Search for hybrid vector + keyword retrieval (ADR-0009).
// MUST use aadOrApiKey auth so ACA managed identity can authenticate via RBAC.

@description('Resource name prefix')
param resourcePrefix string

@description('Azure region')
param location string

@description('Search SKU — basic for dev, standard for prod')
param skuName string = 'basic'

resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: '${resourcePrefix}-search'
  location: location
  sku: {
    name: skuName
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    // CRITICAL: aadOrApiKey enables managed identity auth from ACA.
    // Default (apiKeyOnly) would block RBAC-based access.
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

output searchName string = searchService.name
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchId string = searchService.id
