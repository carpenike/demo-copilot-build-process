// openai.bicep — Azure OpenAI Service with model deployments (ADR-0010).
// MUST use customSubDomainName for managed identity (token) auth.

@description('Resource name prefix')
param resourcePrefix string

@description('Azure region')
param location string

@description('GPT-4o model deployment capacity (TPM in thousands)')
param gpt4oCapacity int = 30

@description('GPT-4o-mini model deployment capacity (TPM in thousands)')
param gpt4oMiniCapacity int = 30

@description('text-embedding-3-large model deployment capacity (TPM in thousands)')
param embeddingCapacity int = 120

resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${resourcePrefix}-openai'
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    // CRITICAL: customSubDomainName required for managed identity auth.
    // Without this, Azure rejects token auth with:
    // "Please provide a custom subdomain for token authentication"
    customSubDomainName: '${resourcePrefix}-openai'
    publicNetworkAccess: 'Enabled'
  }
}

resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: gpt4oCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
}

resource gpt4oMiniDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: 'gpt-4o-mini'
  dependsOn: [gpt4oDeployment]
  sku: {
    name: 'Standard'
    capacity: gpt4oMiniCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: 'text-embedding-3-large'
  dependsOn: [gpt4oMiniDeployment]
  sku: {
    name: 'Standard'
    capacity: embeddingCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
  }
}

output openAiName string = openAi.name
output openAiEndpoint string = openAi.properties.endpoint
output openAiId string = openAi.id
