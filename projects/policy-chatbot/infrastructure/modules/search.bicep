// search.bicep — Azure AI Search
// Policy Chatbot — ADR-0010, ADR-0011: RAG retrieval + document indexing

@description('Resource name prefix for naming resources')
param resourcePrefix string

@description('Azure region for resource deployment')
param location string

@description('Environment tag (dev, staging, production)')
param environment string

@description('Azure AI Search SKU')
param skuName string = 'basic'

var searchName = '${resourcePrefix}-search'

// ─── Azure AI Search ───────────────────────────────────────────────────────────
resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: searchName
  location: location
  sku: {
    name: environment == 'production' ? 'standard' : skuName
  }
  properties: {
    replicaCount: environment == 'production' ? 2 : 1
    partitionCount: 1
    hostingMode: 'default'
    // CRITICAL: Enable AAD auth so ACA managed identity can authenticate via RBAC.
    // Default 'apiKeyOnly' blocks managed identity access with 403.
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

// ─── Outputs ───────────────────────────────────────────────────────────────────
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchName string = searchService.name
output searchId string = searchService.id
