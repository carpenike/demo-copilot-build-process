// ──────────────────────────────────────────────────────────────────────────────
// Azure Cache for Redis (ADR-0009)
// Session state, conversation context, Celery broker
// ──────────────────────────────────────────────────────────────────────────────

param location string
param resourcePrefix string
param skuName string
param capacity int

var redisName = '${resourcePrefix}-redis'

resource redis 'Microsoft.Cache/redis@2024-03-01' = {
  name: redisName
  location: location
  properties: {
    sku: {
      name: skuName
      family: skuName == 'Basic' ? 'C' : 'C'
      capacity: capacity
    }
    enableNonSslPort: false // TLS 1.2+ enforced (NFR-011)
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      'maxmemory-policy': 'volatile-lru'
    }
  }
}

output redisHostName string = redis.properties.hostName
output redisPort int = redis.properties.sslPort
output redisName string = redis.name
