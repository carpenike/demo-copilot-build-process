using 'main.bicep'

param environment = 'staging'
param projectName = 'policy-chatbot'
param imageTag = 'latest'
param acrLoginServer = readEnvironmentVariable('ACR_LOGIN_SERVER', 'acmeacr.azurecr.io')
param postgresAdminPassword = readEnvironmentVariable('POSTGRES_ADMIN_PASSWORD', '')
param redisAccessKey = readEnvironmentVariable('REDIS_ACCESS_KEY', '')
param entraTenantId = readEnvironmentVariable('ENTRA_TENANT_ID', '')
param entraClientId = readEnvironmentVariable('ENTRA_CLIENT_ID', '')
param entraClientSecret = readEnvironmentVariable('ENTRA_CLIENT_SECRET', '')
param azureOpenAIEndpoint = readEnvironmentVariable('AZURE_OPENAI_ENDPOINT', '')
param azureSearchEndpoint = readEnvironmentVariable('AZURE_SEARCH_ENDPOINT', '')
param servicenowInstanceUrl = readEnvironmentVariable('SERVICENOW_INSTANCE_URL', '')
param corsAllowedOrigins = ['https://intranet-staging.acme.com']
