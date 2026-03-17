using 'main.bicep'

param environment = 'production'
param imageTag = 'latest'
param acrLoginServer = readEnvironmentVariable('ACR_LOGIN_SERVER', '')
param acrName = readEnvironmentVariable('ACR_NAME', '')
param postgresAdminPassword = readEnvironmentVariable('POSTGRES_ADMIN_PASSWORD', '')
param entraIdClientId = readEnvironmentVariable('ENTRA_CLIENT_ID', '')
param entraIdClientSecret = readEnvironmentVariable('ENTRA_CLIENT_SECRET', '')
param databaseLocation = ''

// Production: larger SKUs for 200+ concurrent conversations
param apiMinReplicas = 2
param apiMaxReplicas = 10
param workerMinReplicas = 1
param workerMaxReplicas = 5
param postgresSkuName = 'Standard_D2ds_v4'
param postgresSkuTier = 'GeneralPurpose'
param redisSkuName = 'Standard'
param searchSkuName = 'standard'
