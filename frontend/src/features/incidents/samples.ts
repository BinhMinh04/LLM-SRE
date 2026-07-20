// Canonical incident shapes, copied verbatim from backend/tests/samples/*.json.
// Used to pre-fill the "New incident" modal so the pipeline can be tested in one click.

export const SAMPLE_INFRA_OOM = {
  service: 'payment-service',
  cluster: 'prod-fargate',
  started_at: '2026-08-14 14:02:11',
  ecs: {
    running: 1,
    desired: 4,
    stopped_reason: 'OutOfMemory',
    restarts_5m: 11,
    task_memory: '512 MiB',
  },
  alb: {
    healthy: 1,
    total: 4,
    error_rate: '23.7%',
    p95_latency: '4.8s',
    rpm: 3140,
  },
  recent_deploy: {
    service: 'payment-service',
    version: 'v2.14.0',
    by: 'ci-pipeline',
    relative_time: '3 min before incident',
  },
  metrics: {
    memory_pct: '99%',
    cpu_pct: '62%',
    '5xx_rate': '23.7%',
  },
  sample_logs: [
    { ts: '14:02:09', level: 'FATAL', message: 'java.lang.OutOfMemoryError: Java heap space' },
    { ts: '14:02:09', level: 'ERROR', message: 'Container payment killed - exit 137 (OOMKilled)' },
    { ts: '14:02:31', level: 'FATAL', message: 'OutOfMemoryError: Java heap space', count: 9 },
  ],
} as const

export const SAMPLE_APICOST = {
  service: 'gcm-search-gateway',
  started_at: '2026-08-14 13:00:00',
  alert:
    'Total third-party API calls (across endpoints: search + business-detail + ai-chat) are pacing above the daily budget. The vendor bills $0.05/call above 10,000 calls/day. WARNING threshold ~9k/day, CRITICAL at 10k/day. Suspected caching regression from a recent release still active.',
  recent_deploy: {
    service: 'gcm-search-gateway',
    version: 'r2026.07.2',
    by: 'ci-pipeline',
    relative_time: '2 days ago, changed the search-result cache layer',
  },
  metrics: {
    calls_today: 11800,
    daily_budget_calls: 10000,
    calls_per_hour: 600,
    billable_overage_calls: 1800,
    projected_extra_cost_usd: 'approx $90/day if this pace holds',
    cache_hit_rate: '31% (baseline ~88%)',
  },
  sample_logs: [
    {
      ts: '12:58:04',
      level: 'WARN',
      message: 'search cache MISS key=q:restaurants:geo (fallback to upstream API)',
      count: 420,
    },
    { ts: '12:58:41', level: 'INFO', message: 'upstream vendor-search-api call ok status=200 latency=180ms' },
    {
      ts: '12:59:12',
      level: 'WARN',
      message: 'cache layer returned null for TTL-eligible key (unexpected)',
      count: 137,
    },
  ],
  runbook: 'https://internal.example.com/runbooks/api-overage',
} as const
