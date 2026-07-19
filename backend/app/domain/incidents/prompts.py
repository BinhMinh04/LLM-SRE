"""The Step 0 analysis brain's prompt + context rendering, relocated into the domain (decision 0015).

`SYSTEM_PROMPT` and `build_user_message()` are preserved verbatim from the original
`backend/ai/analyze_incident.py` — the anti-hallucination rules and the compact "only print fields
that are present" rendering are the heart of the analysis and must not be rewritten. They are pure
(no I/O), so they belong in the domain and are shared by the analyzer (M2) and, later, the diagnosis
and critic agents (M3).
"""

from __future__ import annotations

# The core of Step 0: anti-hallucination rules + a strict JSON output schema.
SYSTEM_PROMPT = """You are a senior SRE triaging a production incident. \
You receive automatically-collected context and must analyze it quickly and accurately so on-call can act immediately. \
The context may be an infrastructure incident (tasks dying, 5xx...) OR non-infrastructure (third-party API cost over budget, queue backlog...). \
Not every incident has every kind of data — work with what is provided.

MANDATORY RULES:
- Base conclusions ONLY on the provided data. Do NOT invent metrics, service names, or events not present in the context.
- If the data is insufficient to determine the cause, say so explicitly and point out what else to check.
- When reasoning about root cause, connect timestamps (when the anomaly started vs when a deploy/change happened) and cite concrete evidence from the context.
- Write concisely, in the voice of an engineer working the incident. No rambling.

Return ONLY a single valid JSON object, with NO explanation or markdown, following this schema:
{
  "severity": "critical" | "warning" | "info",
  "summary": "1-2 sentences: what is happening and the impact",
  "root_cause": "root-cause reasoning with evidence and timestamps; if uncertain, state the most likely hypothesis with a confidence level",
  "recommended_action": "concrete action to take now, prioritizing stopping the damage first",
  "confidence": "high" | "medium" | "low"
}"""


def build_user_message(ctx: dict) -> str:
    """Assemble the context into a COMPACT LLM input. Only prints sections that have
    data → handles both infra and non-infra incidents, and saves tokens."""
    lines = [f"Service: {ctx.get('service')}"]
    if ctx.get("cluster"):
        lines[0] += f"  |  Cluster: {ctx.get('cluster')}"
    if ctx.get("started_at"):
        lines.append(f"Started at: {ctx.get('started_at')}")

    # Alert description (if the alert carries one — e.g. a cost-threshold violation)
    if ctx.get("alert"):
        lines.append(f"\n[ALERT] {ctx['alert']}")

    ecs = ctx.get("ecs")
    if ecs:
        lines.append(
            f"\n[ECS] running/desired={ecs.get('running')}/{ecs.get('desired')}, "
            f"stopped_reason={ecs.get('stopped_reason')}, restart_5m={ecs.get('restarts_5m')}, "
            f"task_memory={ecs.get('task_memory')}"
        )

    alb = ctx.get("alb")
    if alb:
        lines.append(
            f"[ALB] healthy/total={alb.get('healthy')}/{alb.get('total')}, "
            f"5xx_rate={alb.get('error_rate')}, p95_latency={alb.get('p95_latency')}, "
            f"req_per_min={alb.get('rpm')}"
        )

    dep = ctx.get("recent_deploy")
    if dep:
        lines.append(
            f"[RECENT CHANGE] {dep.get('service')} -> {dep.get('version')} "
            f"by {dep.get('by')}, {dep.get('relative_time')}"
        )

    metrics = ctx.get("metrics")
    if metrics:
        lines.append("[METRICS] " + ", ".join(f"{k}={v}" for k, v in metrics.items()))

    logs = ctx.get("sample_logs")
    if logs:
        lines.append("\n[SAMPLE LOGS] (filtered, with repeat counts)")
        for lg in logs:
            rep = f" x{lg['count']} times" if lg.get("count") else ""
            lines.append(f"  {lg.get('ts')} {lg.get('level')} {lg.get('message')}{rep}")

    if ctx.get("runbook"):
        lines.append(f"\n[RUNBOOK] {ctx['runbook']}")

    return "\n".join(lines)
