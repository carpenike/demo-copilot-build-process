// cache.bicep — Azure Cache for Redis
// Used as Celery broker + conversation context session cache (ADR-0009).

@description('Resource name prefix')
param resourcePrefix string

@description('Azure region')
param location string

@description('Redis SKU — Basic for dev, Standard for prod')
param skuName string = 'Basic'

@description('Redis cache size — C0 (250MB) for dev, C1 (1GB) for prod')
param skuFamily string = 'C'
param skuCapacity int = 0

resource redisCache 'Microsoft.Cache/redis@2024-03-01' = {
  name: '${resourcePrefix}-redis'
  location: location
  properties: {
    sku: {
      name: skuName
      family: skuFamily
      capacity: skuCapacity
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      'maxmemory-policy': 'volatile-lru'
    }
  }
}

output hostname string = redisCache.properties.hostName
output sslPort int = redisCache.properties.sslPort
output primaryKey string = redisCache.listKeys().primaryKey
output name string = redisCache.name
