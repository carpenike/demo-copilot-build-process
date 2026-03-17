using 'main.bicep'

param environment = 'staging'
param imageTag = 'latest'
param acrLoginServer = readEnvironmentVariable('ACR_LOGIN_SERVER', '')
param acrName = readEnvironmentVariable('ACR_NAME', '')
param postgresAdminPassword = readEnvironmentVariable('POSTGRES_ADMIN_PASSWORD', '')
param entraIdClientId = readEnvironmentVariable('ENTRA_CLIENT_ID', '')
param entraIdClientSecret = readEnvironmentVariable('ENTRA_CLIENT_SECRET', '')
param databaseLocation = ''
param openAiLocation = 'eastus'

// Staging: moderate SKUs
param apiMinReplicas = 2
param apiMaxReplicas = 5
param workerMinReplicas = 1
param workerMaxReplicas = 3
param postgresSkuName = 'Standard_B2ms'
param postgresSkuTier = 'Burstable'
param redisSkuName = 'Standard'
param searchSkuName = 'basic'
