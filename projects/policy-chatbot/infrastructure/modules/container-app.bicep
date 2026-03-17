// ──────────────────────────────────────────────────────────────────────────────
// Azure Container Apps — API server for the Policy Chatbot (ADR-0008)
// ──────────────────────────────────────────────────────────────────────────────

param location string
param resourcePrefix string
param imageTag string
param acrLoginServer string
param logAnalyticsWorkspaceId string
param appInsightsConnectionString string
param keyVaultUri string
param searchEndpoint string
param openAIEndpoint string
param entraTenantId string
param entraClientId string
param servicenowInstanceUrl string
param blobAccountUrl string
param corsAllowedOrigins array
param externalIngress bool = false
param minReplicas int
param maxReplicas int
param cpuCores string
param memory string

// ─── Container App Environment ──────────────────────────────────────────────

resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${resourcePrefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
  }
}

// ─── Container App — API Server ─────────────────────────────────────────────

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${resourcePrefix}-api'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: externalIngress
        targetPort: 8000
        transport: 'http'
        corsPolicy: !empty(corsAllowedOrigins) ? {
          allowedOrigins: corsAllowedOrigins
          allowedMethods: ['GET', 'POST', 'PATCH', 'OPTIONS']
          allowedHeaders: ['Authorization', 'Content-Type']
          allowCredentials: true
        } : null
      }
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
        {
          name: 'entra-client-secret'
          keyVaultUrl: '${keyVaultUri}secrets/entra-client-secret'
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
          name: 'api'
          image: '${acrLoginServer}/policy-chatbot:${imageTag}'
          resources: {
            cpu: json(cpuCores)
            memory: memory
          }
          env: [
            { name: 'POLICYCHAT_DEBUG', value: externalIngress ? 'true' : 'false' }
            { name: 'POLICYCHAT_DATABASE_URL', secretRef: 'db-connection-string' }
            { name: 'POLICYCHAT_REDIS_URL', secretRef: 'redis-connection-string' }
            { name: 'POLICYCHAT_ENTRA_TENANT_ID', value: entraTenantId }
            { name: 'POLICYCHAT_ENTRA_CLIENT_ID', value: entraClientId }
            { name: 'POLICYCHAT_ENTRA_CLIENT_SECRET', secretRef: 'entra-client-secret' }
            { name: 'POLICYCHAT_AZURE_OPENAI_ENDPOINT', value: openAIEndpoint }
            { name: 'POLICYCHAT_AZURE_SEARCH_ENDPOINT', value: searchEndpoint }
            { name: 'POLICYCHAT_BLOB_ACCOUNT_URL', value: blobAccountUrl }
            { name: 'POLICYCHAT_SERVICENOW_INSTANCE_URL', value: servicenowInstanceUrl }
            { name: 'POLICYCHAT_SERVICENOW_API_USER', value: 'placeholder' }
            { name: 'POLICYCHAT_SERVICENOW_API_PASSWORD', value: 'placeholder' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
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
                path: '/ready'
                port: 8000
              }
              periodSeconds: 10
              failureThreshold: 5
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

output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output containerAppIdentityPrincipalId string = containerApp.identity.principalId
