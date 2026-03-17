using 'main.bicep'

param environment = 'dev'
param imageTag = 'latest'
param acrLoginServer = readEnvironmentVariable('ACR_LOGIN_SERVER', '')
param acrName = readEnvironmentVariable('ACR_NAME', '')
param postgresAdminPassword = readEnvironmentVariable('POSTGRES_ADMIN_PASSWORD', '')
param entraIdClientId = readEnvironmentVariable('ENTRA_CLIENT_ID', '')
param entraIdClientSecret = readEnvironmentVariable('ENTRA_CLIENT_SECRET', '')
param databaseLocation = ''

// Dev: smaller SKUs to reduce cost
param apiMinReplicas = 1
param apiMaxReplicas = 3
param workerMinReplicas = 1
param workerMaxReplicas = 2
param postgresSkuName = 'Standard_B1ms'
param postgresSkuTier = 'Burstable'
param redisSkuName = 'Basic'
param searchSkuName = 'basic'
