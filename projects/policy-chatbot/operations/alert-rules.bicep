// ──────────────────────────────────────────────────────────────────────────────
// Alert Rules — Policy Chatbot
// Azure Monitor Bicep resources (enterprise standards — no Prometheus YAML)
// Every alert includes a runbook URL in its description.
// Thresholds derived from SLO targets in slo-definitions.md.
// ──────────────────────────────────────────────────────────────────────────────

param projectName string = 'policy-chatbot'
param location string = resourceGroup().location
param applicationInsightsId string
param criticalActionGroupId string
param warningActionGroupId string

param tags object = {
  project: projectName
  managedBy: 'bicep'
}

// ─── HighErrorRate (SLO: 99.5% availability → threshold 0.5% error rate) ────

resource highErrorRate 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-high-error-rate'
  location: location
  tags: tags
  properties: {
    description: '5xx error rate > 0.5% for 5 minutes. SLO target: 99.5% availability (NFR-004). Runbook: https://runbooks.internal/policy-chatbot#high-error-rate'
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
        criticalActionGroupId
      ]
    }
  }
}

// ─── HighLatency (SLO: p95 < 5000ms per NFR-001) ───────────────────────────

resource highLatency 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-high-latency'
  location: location
  tags: tags
  properties: {
    description: 'p95 latency > 5000ms for 15 minutes. SLO target: p95 < 5s (NFR-001). Runbook: https://runbooks.internal/policy-chatbot#high-latency'
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
        warningActionGroupId
      ]
    }
  }
}

// ─── ServiceDown (no healthy container replicas) ────────────────────────────

param containerAppId string

resource serviceDown 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-service-down'
  location: 'global'
  tags: tags
  properties: {
    description: 'No healthy container replicas for 5 minutes. Runbook: https://runbooks.internal/policy-chatbot#service-down'
    severity: 0
    enabled: true
    scopes: [
      containerAppId
    ]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'NoHealthyReplicas'
          metricName: 'Replicas'
          metricNamespace: 'Microsoft.App/containerApps'
          operator: 'LessThanOrEqual'
          threshold: 0
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

// ─── HighMemoryUsage (> 80% of limit) ──────────────────────────────────────

resource highMemoryUsage 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-high-memory-usage'
  location: 'global'
  tags: tags
  properties: {
    description: 'Container memory > 80% of allocated limit for 10 minutes. Runbook: https://runbooks.internal/policy-chatbot#high-memory-usage'
    severity: 2
    enabled: true
    scopes: [
      containerAppId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT10M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'HighMemory'
          metricName: 'UsageNanoCores'
          metricNamespace: 'Microsoft.App/containerApps'
          operator: 'GreaterThan'
          threshold: 80
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: warningActionGroupId
      }
    ]
  }
}

// ─── SLOBurnRateFast (error budget burning > 2x rate for 5 min) ─────────────

resource sloBurnRateFast 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-slo-burn-rate-fast'
  location: location
  tags: tags
  properties: {
    description: 'Error budget burning at > 2x rate (fast burn). 99.5% SLO with 216 min/month budget. Runbook: https://runbooks.internal/policy-chatbot#slo-burn-rate-fast'
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
            | extend error_rate = todouble(errors) / todouble(total)
            | extend burn_rate = error_rate / 0.005
            | where burn_rate > 2
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

// ─── SLOBurnRateSlow (error budget burning > 1x rate for 1h) ────────────────

resource sloBurnRateSlow 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-slo-burn-rate-slow'
  location: location
  tags: tags
  properties: {
    description: 'Error budget burning at > 1x rate for 1 hour (slow burn). 99.5% SLO. Runbook: https://runbooks.internal/policy-chatbot#slo-burn-rate-slow'
    severity: 2
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT15M'
    windowSize: 'PT1H'
    criteria: {
      allOf: [
        {
          query: '''
            requests
            | where timestamp > ago(1h)
            | where name !in ("/health", "/ready")
            | summarize total = count(), errors = countif(resultCode startswith "5")
            | extend error_rate = todouble(errors) / todouble(total)
            | extend burn_rate = error_rate / 0.005
            | where burn_rate > 1
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

// ─── LLMUnavailable (Azure OpenAI fallback triggered — NFR-006) ─────────────

resource llmUnavailable 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-llm-unavailable'
  location: location
  tags: tags
  properties: {
    description: 'Azure OpenAI fallback mode triggered > 5 times in 10 min (NFR-006). Runbook: https://runbooks.internal/policy-chatbot#llm-unavailable'
    severity: 1
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
            customEvents
            | where timestamp > ago(10m)
            | where name == "ChatResponse"
            | where customDimensions.response_type == "fallback_search"
            | summarize fallback_count = count()
            | where fallback_count > 5
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

// ─── HighEscalationRate (> 30% escalation for 24h) ──────────────────────────

resource highEscalationRate 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-high-escalation-rate'
  location: location
  tags: tags
  properties: {
    description: 'Escalation rate > 30% over 24 hours. Business target: ≥ 70% self-service resolution. Runbook: https://runbooks.internal/policy-chatbot#high-escalation-rate'
    severity: 2
    enabled: true
    scopes: [
      applicationInsightsId
    ]
    evaluationFrequency: 'PT1H'
    windowSize: 'P1D'
    criteria: {
      allOf: [
        {
          query: '''
            customEvents
            | where timestamp > ago(24h)
            | where name == "ConversationClosed"
            | summarize
                total = count(),
                escalated = countif(customDimensions.status == "escalated")
            | extend escalation_rate = todouble(escalated) / todouble(total)
            | where escalation_rate > 0.30
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
