// alert-rules.bicep — Azure Monitor Alert Rules for Policy Chatbot
//
// Produced by: @6-monitor agent
// Standards: governance/enterprise-standards.md § Observability Requirements
//
// All alerts defined as Azure Monitor Bicep resources.
// Every alert includes a runbook URL in its description.
// Thresholds derived from SLO targets in slo-definitions.md.
//
// Source NFRs:
//   NFR-001: p95 < 5000ms for chat responses
//   NFR-004: 99.5% availability
//   NFR-006: LLM fallback on outage
//   NFR-013: 200 concurrent conversations (600 peak)

// ─── Parameters ─────────────────────────────────────────────────────────────

@description('Project name used for resource naming')
param projectName string = 'policy-chatbot'

@description('Azure region for alert rule resources')
param location string = resourceGroup().location

@description('Resource ID of the Application Insights instance')
param applicationInsightsId string

@description('Action group for critical (Sev 0/1) alerts — pages on-call')
param criticalActionGroupId string

@description('Action group for warning (Sev 2/3) alerts — creates ticket')
param warningActionGroupId string

@description('Resource ID of the Azure Container App')
param containerAppId string

param tags object = {
  project: projectName
  managedBy: 'bicep'
  component: 'monitoring'
}

// ─── High Error Rate (Availability SLO) ─────────────────────────────────────
// NFR-004: 99.5% availability → error rate threshold 0.5%
// Alert fires at 1% (2x burn rate) for fast detection

resource highErrorRate 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-high-error-rate'
  location: location
  tags: tags
  properties: {
    description: '5xx error rate > 1% for 5 minutes — SLO burn rate > 2x (SLO target: 99.5% availability, NFR-004). Runbook: https://runbooks.internal/${projectName}#high-error-rate'
    severity: 0
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: '''
            requests
            | where timestamp > ago(5m)
            | where name !in ("/health", "/ready")
            | summarize total = count(), errors = countif(resultCode startswith "5")
            | where total > 10
            | extend error_rate = todouble(errors) / todouble(total)
            | where error_rate > 0.01
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
        }
      ]
    }
    actions: {
      actionGroups: [
        criticalActionGroupId
      ]
    }
  }
}

// ─── High Latency — Chat Endpoint (Latency SLO) ────────────────────────────
// NFR-001: p95 < 5000ms for 95% of queries
// Alert fires when p95 > 5000ms over 15 minutes (3 consecutive windows)

resource highLatencyChat 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-high-latency-chat'
  location: location
  tags: tags
  properties: {
    description: 'Chat endpoint p95 latency > 5000ms for 15 minutes (SLO target: p95 < 5000ms, NFR-001). Runbook: https://runbooks.internal/${projectName}#high-latency-chat'
    severity: 1
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      allOf: [
        {
          query: '''
            requests
            | where timestamp > ago(15m)
            | where name startswith "/v1/chat"
            | summarize p95_duration_ms = percentile(duration, 95)
            | where p95_duration_ms > 5000
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
        }
      ]
    }
    actions: {
      actionGroups: [
        criticalActionGroupId
      ]
    }
  }
}

// ─── High Latency — Non-Chat Endpoints ──────────────────────────────────────
// General API endpoints should respond within 1 second at p99

resource highLatencyApi 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-high-latency-api'
  location: location
  tags: tags
  properties: {
    description: 'Non-chat API p99 latency > 1000ms for 15 minutes. Runbook: https://runbooks.internal/${projectName}#high-latency-api'
    severity: 2
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      allOf: [
        {
          query: '''
            requests
            | where timestamp > ago(15m)
            | where name !in ("/health", "/ready")
            | where name !startswith "/v1/chat"
            | summarize p99_duration_ms = percentile(duration, 99)
            | where p99_duration_ms > 1000
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
        }
      ]
    }
    actions: {
      actionGroups: [
        warningActionGroupId
      ]
    }
  }
}

// ─── Service Down (No Healthy Instances) ────────────────────────────────────

resource serviceDown 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-service-down'
  location: 'global'
  tags: tags
  properties: {
    description: 'No healthy container instances detected. Runbook: https://runbooks.internal/${projectName}#service-down'
    severity: 0
    enabled: true
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    scopes: [
      containerAppId
    ]
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'ReplicaCount'
          metricNamespace: 'Microsoft.App/containerApps'
          metricName: 'Replicas'
          operator: 'LessThan'
          threshold: 1
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: criticalActionGroupId
      }
    ]
  }
}

// ─── High Memory Usage ──────────────────────────────────────────────────────

resource highMemoryUsage 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-high-memory-usage'
  location: location
  tags: tags
  properties: {
    description: 'Container memory usage > 80% of limit for 10 minutes. Runbook: https://runbooks.internal/${projectName}#high-memory-usage'
    severity: 2
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT10M'
    criteria: {
      allOf: [
        {
          query: '''
            performanceCounters
            | where timestamp > ago(10m)
            | where category == "Process"
            | where name == "Private Bytes"
            | summarize avg_memory = avg(value)
            | where avg_memory > 0.8 * 1073741824
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
        }
      ]
    }
    actions: {
      actionGroups: [
        warningActionGroupId
      ]
    }
  }
}

// ─── SLO Burn Rate — Fast (Availability) ────────────────────────────────────
// 99.5% SLO → 0.5% error budget. Fast burn = >2x rate = >1% error rate in 5min window

resource sloBurnRateFast 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-slo-burn-fast'
  location: location
  tags: tags
  properties: {
    description: 'Availability error budget burning at > 2x sustainable rate (error rate > 1% for 5min). SLO: 99.5% (NFR-004). Runbook: https://runbooks.internal/${projectName}#slo-burn-rate'
    severity: 0
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: '''
            requests
            | where timestamp > ago(5m)
            | where name !in ("/health", "/ready")
            | summarize total = count(), errors = countif(resultCode startswith "5")
            | where total > 10
            | extend error_rate = todouble(errors) / todouble(total)
            | where error_rate > 0.01
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
        }
      ]
    }
    actions: {
      actionGroups: [
        criticalActionGroupId
      ]
    }
  }
}

// ─── SLO Burn Rate — Slow (Availability) ────────────────────────────────────
// Slow burn = >1x rate = >0.5% error rate sustained over 1h

resource sloBurnRateSlow 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-slo-burn-slow'
  location: location
  tags: tags
  properties: {
    description: 'Availability error budget burning at > 1x sustainable rate for 1 hour (error rate > 0.5%). SLO: 99.5% (NFR-004). Runbook: https://runbooks.internal/${projectName}#slo-burn-rate'
    severity: 2
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    criteria: {
      allOf: [
        {
          query: '''
            requests
            | where timestamp > ago(1h)
            | where name !in ("/health", "/ready")
            | summarize total = count(), errors = countif(resultCode startswith "5")
            | where total > 50
            | extend error_rate = todouble(errors) / todouble(total)
            | where error_rate > 0.005
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
        }
      ]
    }
    actions: {
      actionGroups: [
        warningActionGroupId
      ]
    }
  }
}

// ─── LLM Dependency Failure ─────────────────────────────────────────────────
// NFR-006: System must fall back to keyword search when LLM is unavailable

resource llmDependencyFailure 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-llm-dependency-failure'
  location: location
  tags: tags
  properties: {
    description: 'Azure OpenAI dependency failure rate > 10% for 5 minutes — keyword fallback mode likely active (NFR-006). Runbook: https://runbooks.internal/${projectName}#llm-dependency-failure'
    severity: 1
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: '''
            dependencies
            | where timestamp > ago(5m)
            | where target contains "openai"
            | summarize total = count(), failures = countif(success == false)
            | where total > 5
            | extend failure_rate = todouble(failures) / todouble(total)
            | where failure_rate > 0.10
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
        }
      ]
    }
    actions: {
      actionGroups: [
        criticalActionGroupId
      ]
    }
  }
}

// ─── Database Connection Failure ────────────────────────────────────────────

resource databaseFailure 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-database-failure'
  location: location
  tags: tags
  properties: {
    description: 'PostgreSQL dependency failure rate > 10% for 5 minutes. Runbook: https://runbooks.internal/${projectName}#database-connection-failure'
    severity: 0
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: '''
            dependencies
            | where timestamp > ago(5m)
            | where type == "SQL" or target contains "postgres"
            | summarize total = count(), failures = countif(success == false)
            | where total > 5
            | extend failure_rate = todouble(failures) / todouble(total)
            | where failure_rate > 0.10
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
        }
      ]
    }
    actions: {
      actionGroups: [
        criticalActionGroupId
      ]
    }
  }
}

// ─── Search Index Staleness ─────────────────────────────────────────────────
// NFR-002: Single document indexing within 5 minutes

resource searchIndexStale 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-search-index-stale'
  location: location
  tags: tags
  properties: {
    description: 'Document indexing job exceeded 5-minute SLO (NFR-002). Runbook: https://runbooks.internal/${projectName}#search-index-stale'
    severity: 2
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT10M'
    criteria: {
      allOf: [
        {
          query: '''
            customMetrics
            | where timestamp > ago(10m)
            | where name == "document_indexing_duration_seconds"
            | where value > 300
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
        }
      ]
    }
    actions: {
      actionGroups: [
        warningActionGroupId
      ]
    }
  }
}

// ─── High Concurrent Connections ────────────────────────────────────────────
// NFR-013: 200 concurrent conversations normal, 600 peak

resource highConcurrency 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-high-concurrency'
  location: location
  tags: tags
  properties: {
    description: 'Active requests approaching capacity limit (>150 of 200 normal capacity, NFR-013). Runbook: https://runbooks.internal/${projectName}#high-concurrency'
    severity: 2
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: '''
            requests
            | where timestamp > ago(5m)
            | summarize concurrent = dcount(id) by bin(timestamp, 1s)
            | summarize max_concurrent = max(concurrent)
            | where max_concurrent > 150
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
        }
      ]
    }
    actions: {
      actionGroups: [
        warningActionGroupId
      ]
    }
  }
}
