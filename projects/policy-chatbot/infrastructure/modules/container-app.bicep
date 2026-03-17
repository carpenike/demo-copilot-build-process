// container-app.bicep — Azure Container App for the policy chatbot API and worker.

@description('Resource name prefix')
param resourcePrefix string

@description('Azure region')
param location string

@description('ACA Environment ID')
param environmentId string

@description('Container image tag')
param imageTag string

@description('ACR login server (e.g. myregistry.azurecr.io)')
param acrLoginServer string

@description('Image name')
param imageName string = 'policy-chatbot'

@description('Minimum replicas')
param minReplicas int = 2

@description('Maximum replicas')
param maxReplicas int = 10

@description('CPU cores per replica')
param cpu string = '0.5'

@description('Memory per replica')
param memory string = '1Gi'

@description('Whether this is the API (true) or worker (false)')
param isApi bool = true

@description('Database URL Key Vault secret URI')
param databaseUrlSecretUri string

@description('Redis URL Key Vault secret URI')
param redisUrlSecretUri string

@description('App Insights connection string Key Vault secret URI')
param appInsightsSecretUri string

@description('Entra ID client secret Key Vault secret URI')
param entraClientSecretUri string

@description('Azure OpenAI endpoint')
param openAiEndpoint string

@description('Azure AI Search endpoint')
param searchEndpoint string

@description('Azure Blob Storage account URL')
param storageAccountUrl string

@description('Entra ID tenant ID')
param tenantId string

@description('Entra ID client ID')
param clientId string

var appName = isApi ? '${resourcePrefix}-api' : '${resourcePrefix}-worker'
var command = isApi
  ? ['uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000', '--workers', '4']
  : ['celery', '-A', 'app.tasks.indexing:get_celery_app', 'worker', '--loglevel=info']

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: isApi
        ? {
            external: true
            targetPort: 8000
            transport: 'http'
            allowInsecure: false
          }
        : null
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: databaseUrlSecretUri
          identity: 'system'
        }
        {
          name: 'redis-url'
          keyVaultUrl: redisUrlSecretUri
          identity: 'system'
        }
        {
          name: 'appinsights-connection-string'
          keyVaultUrl: appInsightsSecretUri
          identity: 'system'
        }
        {
          name: 'entra-client-secret'
          keyVaultUrl: entraClientSecretUri
          identity: 'system'
        }
      ]
      registries: [
        {
          server: acrLoginServer
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: imageName
          image: '${acrLoginServer}/${imageName}:${imageTag}'
          command: command
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            // --- Application ---
            { name: 'POLICY_CHATBOT_APP_NAME', value: appName }
            { name: 'POLICY_CHATBOT_DEBUG', value: 'false' }
            { name: 'POLICY_CHATBOT_LOG_LEVEL', value: 'INFO' }
            // --- Database ---
            { name: 'POLICY_CHATBOT_DATABASE_URL', secretRef: 'database-url' }
            // --- Redis ---
            { name: 'POLICY_CHATBOT_REDIS_URL', secretRef: 'redis-url' }
            // --- Azure OpenAI ---
            { name: 'POLICY_CHATBOT_AZURE_OPENAI_ENDPOINT', value: openAiEndpoint }
            { name: 'POLICY_CHATBOT_AZURE_OPENAI_API_VERSION', value: '2024-12-01-preview' }
            { name: 'POLICY_CHATBOT_AZURE_OPENAI_CHAT_DEPLOYMENT', value: 'gpt-4o' }
            { name: 'POLICY_CHATBOT_AZURE_OPENAI_CLASSIFIER_DEPLOYMENT', value: 'gpt-4o-mini' }
            { name: 'POLICY_CHATBOT_AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: 'text-embedding-3-large' }
            { name: 'POLICY_CHATBOT_AZURE_OPENAI_EMBEDDING_DIMENSIONS', value: '3072' }
            // --- Azure AI Search ---
            { name: 'POLICY_CHATBOT_AZURE_SEARCH_ENDPOINT', value: searchEndpoint }
            { name: 'POLICY_CHATBOT_AZURE_SEARCH_INDEX_NAME', value: 'policy-documents' }
            // --- Azure Blob Storage ---
            { name: 'POLICY_CHATBOT_AZURE_STORAGE_ACCOUNT_URL', value: storageAccountUrl }
            // --- Azure Monitor ---
            {
              name: 'POLICY_CHATBOT_APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'appinsights-connection-string'
            }
            // --- Entra ID ---
            { name: 'POLICY_CHATBOT_AZURE_TENANT_ID', value: tenantId }
            { name: 'POLICY_CHATBOT_AZURE_CLIENT_ID', value: clientId }
            { name: 'POLICY_CHATBOT_AZURE_CLIENT_SECRET', secretRef: 'entra-client-secret' }
            // --- RAG Pipeline ---
            { name: 'POLICY_CHATBOT_RAG_CONFIDENCE_THRESHOLD', value: '0.6' }
            { name: 'POLICY_CHATBOT_RAG_MAX_ESCALATION_ATTEMPTS', value: '2' }
            { name: 'POLICY_CHATBOT_RAG_TOP_K', value: '5' }
          ]
          probes: isApi
            ? [
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
                    path: '/ready'
                    port: 8000
                  }
                  periodSeconds: 10
                  failureThreshold: 3
                  initialDelaySeconds: 5
                }
              ]
            : []
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: isApi
          ? [
              {
                name: 'http-scaling'
                http: {
                  metadata: {
                    concurrentRequests: '20'
                  }
                }
              }
            ]
          : [
              {
                name: 'redis-queue-scaling'
                custom: {
                  type: 'redis'
                  metadata: {
                    listName: 'celery'
                    listLength: '5'
                  }
                  auth: [
                    {
                      secretRef: 'redis-url'
                      triggerParameter: 'address'
                    }
                  ]
                }
              }
            ]
      }
    }
  }
}

output appName string = containerApp.name
output principalId string = containerApp.identity.principalId
output fqdn string = isApi ? containerApp.properties.configuration.ingress.fqdn : ''
