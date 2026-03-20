// container-app.bicep — Azure Container Apps
// Policy Chatbot — ADR-0008: Compute Platform (ACA)

@description('Resource name prefix for naming resources')
param resourcePrefix string

@description('Azure region for resource deployment')
param location string

@description('Environment tag (dev, staging, production)')
param environment string

@description('Container image tag (git SHA)')
param imageTag string

@description('ACR login server (e.g., myacr.azurecr.io)')
param acrLoginServer string

@description('ACA managed environment resource ID')
param managedEnvironmentId string

@description('Key Vault URI for secret references')
param keyVaultUri string

@description('Azure Blob Storage account URL')
param blobAccountUrl string

@description('Blob container name')
param blobContainerName string = 'policy-docs'

@description('Azure AI Search endpoint')
param searchEndpoint string

@description('Azure AI Search index name')
param searchIndexName string = 'policy-chunks'

@description('Azure OpenAI endpoint')
param openAiEndpoint string

@description('GPT-4o deployment name')
param openAiDeployment string = 'gpt-4o'

@description('Embedding model deployment name')
param openAiEmbeddingDeployment string = 'text-embedding-ada-002'

@description('Azure OpenAI API version')
param openAiApiVersion string = '2024-12-01-preview'

@description('Entra ID tenant ID for authentication')
param entraTenantId string

@description('Entra ID client ID for authentication')
param entraClientId string

@description('Entra ID authority URL')
param entraAuthority string

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('Allowed CORS origins')
param allowedOrigins string = 'https://intranet.acme.com'

@description('Minimum replicas')
param minReplicas int = environment == 'production' ? 2 : 0

@description('Maximum replicas')
param maxReplicas int = environment == 'production' ? 10 : 3

var appName = '${resourcePrefix}-api'
var imageName = 'policy-chatbot'

// ─── Container App ─────────────────────────────────────────────────────────────
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: environment != 'production'
        targetPort: 8000
        transport: 'http'
        corsPolicy: {
          allowedOrigins: [allowedOrigins]
          allowedMethods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          maxAge: 3600
        }
      }
      registries: [
        {
          server: acrLoginServer
          identity: 'system'
        }
      ]
      secrets: [
        {
          name: 'db-connection-string'
          keyVaultUrl: '${keyVaultUri}secrets/db-connection-string'
          identity: 'system'
        }
        {
          name: 'redis-connection-string'
          keyVaultUrl: '${keyVaultUri}secrets/redis-connection-string'
          identity: 'system'
        }
      ]
    }
    template: {
      // Do NOT set 'command' — let Docker ENTRYPOINT (entrypoint.sh) + CMD work.
      // ACA 'command' overrides BOTH ENTRYPOINT and CMD, which would skip
      // database migrations in entrypoint.sh.
      containers: [
        {
          name: 'api'
          image: '${acrLoginServer}/${imageName}:${imageTag}'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'POLICY_CHATBOT_APP_NAME', value: 'policy-chatbot' }
            { name: 'POLICY_CHATBOT_DEBUG', value: environment == 'production' ? 'false' : 'true' }
            { name: 'POLICY_CHATBOT_ALLOWED_ORIGINS', value: allowedOrigins }
            { name: 'POLICY_CHATBOT_DATABASE_URL', secretRef: 'db-connection-string' }
            { name: 'POLICY_CHATBOT_REDIS_URL', secretRef: 'redis-connection-string' }
            { name: 'POLICY_CHATBOT_BLOB_ACCOUNT_URL', value: blobAccountUrl }
            { name: 'POLICY_CHATBOT_BLOB_CONTAINER_NAME', value: blobContainerName }
            { name: 'POLICY_CHATBOT_SEARCH_ENDPOINT', value: searchEndpoint }
            { name: 'POLICY_CHATBOT_SEARCH_INDEX_NAME', value: searchIndexName }
            { name: 'POLICY_CHATBOT_OPENAI_ENDPOINT', value: openAiEndpoint }
            { name: 'POLICY_CHATBOT_OPENAI_DEPLOYMENT', value: openAiDeployment }
            { name: 'POLICY_CHATBOT_OPENAI_EMBEDDING_DEPLOYMENT', value: openAiEmbeddingDeployment }
            { name: 'POLICY_CHATBOT_OPENAI_API_VERSION', value: openAiApiVersion }
            { name: 'POLICY_CHATBOT_ENTRA_TENANT_ID', value: entraTenantId }
            { name: 'POLICY_CHATBOT_ENTRA_CLIENT_ID', value: entraClientId }
            { name: 'POLICY_CHATBOT_ENTRA_AUTHORITY', value: entraAuthority }
            { name: 'POLICY_CHATBOT_GRAPH_BASE_URL', value: 'https://graph.microsoft.com/v1.0' }
            { name: 'POLICY_CHATBOT_SERVICENOW_BASE_URL', value: '' }
            { name: 'POLICY_CHATBOT_APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            { name: 'POLICY_CHATBOT_SESSION_TTL_SECONDS', value: '1800' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              periodSeconds: 30
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              periodSeconds: 10
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

// ─── Outputs ───────────────────────────────────────────────────────────────────
output appName string = containerApp.name
output principalId string = containerApp.identity.principalId
output fqdn string = containerApp.properties.configuration.ingress.fqdn
