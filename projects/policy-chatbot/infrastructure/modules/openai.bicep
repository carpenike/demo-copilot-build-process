// openai.bicep — Azure OpenAI Service
// Policy Chatbot — ADR-0010: RAG answer generation (GPT-4o + embeddings)

@description('Resource name prefix for naming resources')
param resourcePrefix string

@description('Azure region for resource deployment')
param location string

@description('GPT-4o model deployment name')
param gptDeploymentName string = 'gpt-4o'

@description('Embedding model deployment name')
param embeddingDeploymentName string = 'text-embedding-ada-002'

var openAiName = '${resourcePrefix}-openai'

// ─── Azure OpenAI Account ──────────────────────────────────────────────────────
// CRITICAL: customSubDomainName is required for token-based auth (managed identity).
// Without it, Azure rejects DefaultAzureCredential with:
// "Please provide a custom subdomain for token authentication"
resource openAiAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openAiName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAiName
    publicNetworkAccess: 'Enabled'
  }
}

// ─── GPT-4o Deployment ─────────────────────────────────────────────────────────
resource gptDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAiAccount
  name: gptDeploymentName
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
}

// ─── Embedding Deployment ──────────────────────────────────────────────────────
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAiAccount
  name: embeddingDeploymentName
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-ada-002'
      version: '2'
    }
  }
  dependsOn: [gptDeployment]
}

// ─── Outputs ───────────────────────────────────────────────────────────────────
output openAiEndpoint string = openAiAccount.properties.endpoint
output openAiName string = openAiAccount.name
output openAiId string = openAiAccount.id
