// cache.bicep — Azure Cache for Redis
// Policy Chatbot — ADR-0009: Data Storage (session state)

@description('Resource name prefix for naming resources')
param resourcePrefix string

@description('Azure region for resource deployment')
param location string

@description('Environment tag (dev, staging, production)')
param environment string

@description('Redis SKU name')
param skuName string = 'Basic'

@description('Redis SKU family')
param skuFamily string = 'C'

@description('Redis cache capacity (0=250MB, 1=1GB, etc.)')
param skuCapacity int = 0

var redisName = '${resourcePrefix}-redis'

// ─── Azure Cache for Redis ─────────────────────────────────────────────────────
resource redis 'Microsoft.Cache/redis@2024-03-01' = {
  name: redisName
  location: location
  properties: {
    sku: {
      name: environment == 'production' ? 'Standard' : skuName
      family: skuFamily
      capacity: environment == 'production' ? 1 : skuCapacity
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      'maxmemory-policy': 'volatile-lru'
    }
  }
}

// ─── Outputs ───────────────────────────────────────────────────────────────────
output redisHostName string = redis.properties.hostName
output redisPort int = redis.properties.sslPort
output redisName string = redis.name

#disable-next-line outputs-should-not-contain-secrets
output redisPrimaryKey string = redis.listKeys().primaryKey
