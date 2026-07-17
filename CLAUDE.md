# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**LLM-SRE** (internal name **IIM**) is an AI incident-analysis layer for SRE / on-call work. It feeds an
automatically-collected incident context bundle into an LLM (AWS Bedrock, Claude models) and returns a
structured triage analysis as JSON: `severity`, `summary`, `root_cause`, `recommended_action`, `confidence`.

The project is being built in numbered steps. Only **Step 0** exists today: `ai/analyze_incident.py`, a
standalone CLI that needs no AWS infrastructure other than Bedrock access. Later steps (referenced in code
and `.gitignore` but **not yet built**) add persistence and a UI — see Roadmap below. Do not assume that
infrastructure exists; check before referencing it.

## Running (Step 0)

```bash
pip install boto3
export AWS_REGION=ap-southeast-1        # account/role must have Bedrock access to the model
python ai/analyze_incident.py ai/samples/infra_oom.json        # infrastructure incident (OOM/5xx)
python ai/analyze_incident.py ai/samples/apicost_overage.json  # non-infrastructure incident (API cost)
```

Running with a sample calls the LLM once (cache miss), then re-runs the same incident to demonstrate a
cache hit (0 tokens). There is no test suite yet (`.gitignore` anticipates `pytest`).

- **Model / region**: set in constants at the top of `analyze_incident.py` (`MODEL_ID`, `REGION`). Defaults
  to a Haiku model for cost. Region `ap-southeast-1` may require a Bedrock *inference profile* prefix
  (e.g. `apac.anthropic.claude-...`) rather than the bare model id — confirm against the Bedrock console
  (Model access) if a call fails.

## Architecture (`ai/analyze_incident.py`)

The pipeline is: **incident context dict → fingerprint (cache check) → build user message → Bedrock
`converse` → parse JSON → cache**. Four pieces carry the design:

- **`SYSTEM_PROMPT`** — the core of Step 0. Enforces anti-hallucination rules: conclude *only* from provided
  data, never invent metrics/services/events, state explicitly when data is insufficient, and connect
  timestamps (anomaly start vs. deploy time) as evidence. Also fixes the output to a strict JSON schema.
  Changes to analysis behavior usually mean editing this prompt, not the code around it.
- **`build_user_message(ctx)`** — assembles the context into a compact prompt. It only emits sections that
  are present (`ecs`, `alb`, `recent_deploy`, `metrics`, `sample_logs`, `runbook`, `alert`), so the *same*
  function handles both infrastructure incidents and non-infrastructure ones (e.g. third-party API cost
  overage). This "only print what's present" design is deliberate — it saves tokens and keeps one code path
  for all incident shapes. Preserve it when adding new context fields.
- **`fingerprint(ctx)`** — the cache key: `service | normalized-error-signature | deploy-version`. The error
  signature is normalized by stripping digits and hex ids (`re.sub`) so repeats of the same error collapse
  to one key. Crucially, a **different deploy version yields a different fingerprint**, forcing re-analysis
  so a stale cache can't misdiagnose a post-deploy incident.
- **`analyze(ctx)`** — cache-first. On hit, returns the stored result tagged `_cache: HIT (0 tokens)`; on
  miss, calls Bedrock, strips markdown fences from the response, `json.loads` it, caches, and tags
  `_cache: MISS`.

The cache (`_CACHE`) is an in-memory dict with a conceptual TTL constant (`CACHE_TTL_SECONDS`). It is
process-local and not actually time-expired in Step 0.

## Incident context shape

Input is a JSON object describing one incident. All fields are optional except `service`; the two files in
`ai/samples/` are the canonical examples of the two supported shapes:

- **Infrastructure** (`infra_oom.json`): `ecs`, `alb`, `metrics`, `sample_logs`, `recent_deploy`.
- **Non-infrastructure** (`apicost_overage.json`): `alert` (human description) plus `metrics` / `sample_logs`.

When extending the input format, update `build_user_message()` to render the new field and keep the samples
in sync as living documentation.

## Roadmap (planned, not yet implemented)

Referenced by code comments and `.gitignore`, but no files exist for these yet — treat as direction, not
current state:

- **Step 4**: replace the in-memory `_CACHE` with **DynamoDB + TTL**.
- A **React frontend** in `board/` (see `.gitignore`).
- **Serverless / AWS CDK** deployment (`.serverless/`, `cdk.out/` in `.gitignore`).

The full Phase-1 design (problem/goals, architecture + ADRs, DynamoDB data model, build plan, open
questions) is written up in `.claude/specs/`: `SPEC.md`, `ARCHITECTURE.md`, `DATA_MODEL.md`, `PLAN.md`,
`OPEN_QUESTIONS.md`. Read these before implementing any of the steps above — they're the source of truth
for what to build next, not this section.
