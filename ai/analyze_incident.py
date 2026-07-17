"""
IIM — Step 0: Incident analysis AI layer (runs standalone, no other AWS infra needed)

Feed an incident context bundle into an LLM and get back a 3-part analysis as JSON:
summary · root-cause reasoning · recommended action.

Includes: fingerprint + cache-first (token savings) and an anti-hallucination prompt.
build_user_message() is flexible: it only prints fields that are present, so it handles
both infrastructure incidents (OOM/5xx) and non-infrastructure ones (third-party API cost...).

Run:
    pip install boto3
    export AWS_REGION=ap-southeast-1        # needs Bedrock permission
    python analyze_incident.py samples/infra_oom.json

Notes:
- Step 0 uses an in-memory cache (dict). In Step 4 this is replaced by DynamoDB (with TTL).
- Defaults to a Haiku model for cost; upgrade to Sonnet for complex incidents if needed.
"""

import json
import sys
import hashlib
import re
import boto3

# ── Config ────────────────────────────────────────────────────────────────
# Get the current model id from the Bedrock console (Model access). Haiku = cheapest.
# Region ap-southeast-1 may require an inference profile: "apac.anthropic.claude-..."
MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"
REGION = "ap-southeast-1"
CACHE_TTL_SECONDS = 1800  # 30 min — a recurring incident within this window reuses the analysis

# ── Prompt: the heart of Step 0 ───────────────────────────────────────────
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


def fingerprint(ctx: dict) -> str:
    """Cache key: service + error signature + current change version.
    If the change/deploy version differs -> fingerprint differs -> re-analyze
    (prevents a stale cache from misdiagnosing)."""
    if ctx.get("sample_logs"):
        raw = ctx["sample_logs"][0].get("message", "")
    else:
        raw = ctx.get("alert", "")
    error_sig = re.sub(r"[0-9a-f]{8,}|\d+", "", raw).strip()
    version = (ctx.get("recent_deploy") or {}).get("version", "")
    key = f"{ctx.get('service')}|{error_sig}|{version}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# Step 0: in-memory cache. Step 4 replaces this with DynamoDB + TTL.
_CACHE: dict = {}


def analyze(ctx: dict) -> dict:
    """Cache-first: if present in cache, return it (0 tokens). On a miss, call the LLM."""
    fp = fingerprint(ctx)
    if fp in _CACHE:
        result = dict(_CACHE[fp])
        result["_cache"] = "HIT (0 tokens)"
        return result

    client = boto3.client("bedrock-runtime", region_name=REGION)
    resp = client.converse(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": build_user_message(ctx)}]}],
        inferenceConfig={"maxTokens": 600, "temperature": 0.2},
    )
    text = resp["output"]["message"]["content"][0]["text"].strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"error": "Failed to parse JSON", "raw": text}

    _CACHE[fp] = result
    out = dict(result)
    out["_cache"] = "MISS (called LLM)"
    return out


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "samples/infra_oom.json"
    with open(path, encoding="utf-8") as f:
        context = json.load(f)

    print("=== Run 1 (cache miss, calling LLM) ===")
    print(json.dumps(analyze(context), ensure_ascii=False, indent=2))

    print("\n=== Run 2 (same incident -> cache hit, 0 tokens) ===")
    print(json.dumps(analyze(context), ensure_ascii=False, indent=2))