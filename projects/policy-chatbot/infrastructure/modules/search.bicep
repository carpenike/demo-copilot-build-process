// ──────────────────────────────────────────────────────────────────────────────
// Azure AI Search (ADR-0009)
// Vector + keyword index for policy document chunks
// ──────────────────────────────────────────────────────────────────────────────

param location string
param resourcePrefix string
param skuName string
param replicaCount int

var searchName = '${resourcePrefix}-search'

resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: searchName
  location: location
  sku: {
    name: skuName
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount: replicaCount
    partitionCount: 1
    hostingMode: 'default'
    semanticSearch: 'standard' // Enable semantic ranker
    encryptionWithCmk: {
      enforcement: 'Unspecified'
    }
  }
}

output searchServiceName string = searchService.name
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
