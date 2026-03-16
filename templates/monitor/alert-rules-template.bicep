// Alert Rules Template — Azure Monitor Bicep Resources
//
// Produced by: @6-monitor agent
// Standards: governance/enterprise-standards.md § Observability Requirements
//
// All alerts MUST be defined as Azure Monitor Bicep resources.
// Do NOT use Prometheus YAML alert rules or Terraform .tf files.
// Every alert MUST include a runbook URL in its description.
// Thresholds MUST match SLO targets — do not use arbitrary round numbers.
//
// Replace all <placeholders> with project-specific values.

// ─── Parameters ─────────────────────────────────────────────────────────────

param projectName string
param location string = resourceGroup().location
param applicationInsightsId string
param criticalActionGroupId string
param warningActionGroupId string

param tags object = {
  project: projectName
  managedBy: 'bicep'
}

// ─── Availability SLO ───────────────────────────────────────────────────────

resource highErrorRate 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-high-error-rate'
  location: location
  tags: tags
  properties: {
    description: '''
      5xx error rate > <threshold>% for 5 minutes (SLO: <target>%).
      Runbook: https://runbooks.internal/${projectName}#high-error-rate
    '''
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
            | where error_rate > 0.001
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

// ─── Latency SLO ────────────────────────────────────────────────────────────

resource highLatency 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-high-latency'
  location: location
  tags: tags
  properties: {
    description: '''
      p95 latency > <threshold_ms>ms for 15 minutes (SLO: p99 < <target_ms>ms).
      Runbook: https://runbooks.internal/${projectName}#high-latency
    '''
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
            | where p95_duration_ms > <threshold_ms>
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

// ─── Service Health ─────────────────────────────────────────────────────────

// Replace containerAppId with the resource ID of the Azure Container App
param containerAppId string = ''

resource serviceDown 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-service-down'
  location: 'global'
  tags: tags
  properties: {
    description: '''
      No healthy instances detected.
      Runbook: https://runbooks.internal/${projectName}#service-down
    '''
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

// ─── Error Budget Burn Rate (Fast) ──────────────────────────────────────────

resource sloBurnRateFast 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-slo-burn-fast'
  location: location
  tags: tags
  properties: {
    description: '''
      Error budget burning at > 2x sustainable rate.
      Runbook: https://runbooks.internal/${projectName}#slo-burn-rate
    '''
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
            | where error_rate > 0.002
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

// ─── Error Budget Burn Rate (Slow) ──────────────────────────────────────────

resource sloBurnRateSlow 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-slo-burn-slow'
  location: location
  tags: tags
  properties: {
    description: '''
      Error budget burning at > 1x sustainable rate for 1 hour.
      Runbook: https://runbooks.internal/${projectName}#slo-burn-rate
    '''
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
            | extend error_rate = todouble(errors) / todouble(total)
            | where error_rate > 0.001
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
