// alert-rules.bicep — Azure Monitor alert rules for Policy Chatbot
//
// Produced by: @6-monitor agent
// Standards: governance/enterprise-standards.md § Observability Requirements
//
// All alerts are Azure Monitor Bicep resources. No Prometheus YAML or Terraform.
// Every alert includes a runbook URL in its description.
// Thresholds are derived from SLO targets in slo-definitions.md.

// ─── Parameters ─────────────────────────────────────────────────────────────

param projectName string = 'policy-chatbot'
param environment string
param location string = resourceGroup().location
param applicationInsightsId string
param criticalActionGroupId string
param warningActionGroupId string

param tags object = {
  project: projectName
  environment: environment
  managedBy: 'bicep'
}

var runbookBase = 'https://github.com/carpenike/demo-copilot-build-process/blob/main/projects/${projectName}/operations/runbook.md'

// ─── 1. HighErrorRate (SLO: 99.5% availability) ────────────────────────────

resource highErrorRate 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-${environment}-high-error-rate'
  location: location
  tags: tags
  properties: {
    description: '5xx error rate > 0.5% for 5 minutes. SLO: 99.5% availability (NFR-004). Runbook: ${runbookBase}#higherrorrate'
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

// ─── 2. HighLatency (SLO: p95 < 5000ms, NFR-001) ───────────────────────────

resource highLatency 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-${environment}-high-latency'
  location: location
  tags: tags
  properties: {
    description: 'p95 latency > 5000ms for 15 minutes. SLO: p95 < 5s (NFR-001). Runbook: ${runbookBase}#highlatency'
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
            | summarize p95_ms = percentile(duration, 95)
            | where p95_ms > 5000
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

// ─── 3. ServiceDown — zero healthy instances ────────────────────────────────

resource serviceDown 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-${environment}-service-down'
  location: location
  tags: tags
  properties: {
    description: 'No successful requests in 5 minutes — service may be down. Runbook: ${runbookBase}#servicedown'
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
            | summarize request_count = count()
            | where request_count == 0
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

// ─── 4. HighMemoryUsage — memory > 80% of container limit ──────────────────

resource highMemoryUsage 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-${environment}-high-memory'
  location: location
  tags: tags
  properties: {
    description: 'Container memory usage > 80% of limit for 10 minutes. Runbook: ${runbookBase}#highmemoryusage'
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
            | where category == "Process" and counter == "Working Set"
            | summarize avg_memory_bytes = avg(value)
            | extend memory_mb = avg_memory_bytes / 1048576
            | extend limit_mb = 1024
            | extend usage_pct = (memory_mb / limit_mb) * 100
            | where usage_pct > 80
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

// ─── 5. SLOBurnRateFast — error budget burning > 14.4x (exhausts in 1h) ────

resource sloBurnRateFast 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-${environment}-slo-burn-fast'
  location: location
  tags: tags
  properties: {
    description: 'Error budget burning at > 14.4x rate (will exhaust in ~1 hour). SLO: 99.5% (NFR-004). Runbook: ${runbookBase}#sloburnratefast'
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
            let slo_target = 0.995;
            requests
            | where timestamp > ago(5m)
            | where name !in ("/health", "/ready")
            | summarize total = count(), errors = countif(resultCode startswith "5")
            | where total > 10
            | extend error_rate = todouble(errors) / todouble(total)
            | extend burn_rate = error_rate / (1.0 - slo_target)
            | where burn_rate > 14.4
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

// ─── 6. SLOBurnRateSlow — error budget burning > 1x for 1h ─────────────────

resource sloBurnRateSlow 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-${environment}-slo-burn-slow'
  location: location
  tags: tags
  properties: {
    description: 'Error budget burning at > 1x sustained rate for 1 hour. SLO: 99.5% (NFR-004). Runbook: ${runbookBase}#sloburnrateslow'
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
            let slo_target = 0.995;
            requests
            | where timestamp > ago(1h)
            | where name !in ("/health", "/ready")
            | summarize total = count(), errors = countif(resultCode startswith "5")
            | where total > 50
            | extend error_rate = todouble(errors) / todouble(total)
            | extend burn_rate = error_rate / (1.0 - slo_target)
            | where burn_rate > 1.0
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

// ─── 7. LLMDependencyDown — Azure OpenAI failures ──────────────────────────

resource llmDependencyDown 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-${environment}-llm-dependency-down'
  location: location
  tags: tags
  properties: {
    description: 'Azure OpenAI dependency failure rate > 5% for 10 minutes. Keyword fallback should be active (NFR-006). Runbook: ${runbookBase}#llmdependencydown'
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
            dependencies
            | where timestamp > ago(10m)
            | where type == "HTTP" and target contains "openai"
            | summarize total = count(), failures = countif(success == false)
            | where total > 5
            | extend failure_rate = todouble(failures) / todouble(total)
            | where failure_rate > 0.05
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

// ─── 8. HighEscalationRate — auto-escalation rate > 25% ─────────────────────

resource highEscalationRate 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-${environment}-high-escalation-rate'
  location: location
  tags: tags
  properties: {
    description: 'Auto-escalation rate > 25% over 1 hour. Target: < 30% escalation (business objective). Runbook: ${runbookBase}#highescalationrate'
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
            customEvents
            | where timestamp > ago(1h)
            | where name == "analytics_event"
            | where customDimensions.event_type in ("query", "escalation")
            | summarize
                total = countif(customDimensions.event_type == "query"),
                escalations = countif(customDimensions.event_type == "escalation")
            | where total > 20
            | extend escalation_rate = todouble(escalations) / todouble(total)
            | where escalation_rate > 0.25
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
