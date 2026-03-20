using 'main.bicep'

param resourcePrefix = 'policy-chatbot-prod'
param environment = 'production'
param imageTag = 'latest'
param acrLoginServer = readEnvironmentVariable('ACR_LOGIN_SERVER', '')
param acrName = readEnvironmentVariable('ACR_NAME', '')
param postgresAdminPassword = readEnvironmentVariable('POSTGRES_ADMIN_PASSWORD', '')
param postgresSkuName = 'Standard_D2ds_v5'
param postgresSkuTier = 'GeneralPurpose'
param databaseLocation = ''
param entraTenantId = readEnvironmentVariable('ENTRA_TENANT_ID', '')
param entraClientId = readEnvironmentVariable('ENTRA_CLIENT_ID', '')
param entraAuthority = readEnvironmentVariable('ENTRA_AUTHORITY', '')
param allowedOrigins = 'https://intranet.acme.com'
