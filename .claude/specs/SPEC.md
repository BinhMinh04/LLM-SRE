# IIM — Specification (Phase 1)

- **Project:** IIM (Intelligent Incident Management) — repo `LLM-SRE`
- **Date:** 2026-07-17
- **Status:** Draft (Phase 1 design — design only, no implementation)
- **Language:** All artifacts (code, comments, docs, UI, logs) in English.
- **Related:** [ARCHITECTURE.md](./ARCHITECTURE.md) · [DATA_MODEL.md](./DATA_MODEL.md) · [PLAN.md](./PLAN.md) · [OPEN_QUESTIONS.md](./OPEN_QUESTIONS.md)

## 1. Problem

When a production incident occurs on AWS, on-call engineers currently jump between many tools
(CloudWatch, ECS console, log groups, deploy history) to answer two questions: **"what is on fire?"**
and **"why?"**. This context-gathering is slow and manual, which inflates Mean Time To Resolution (MTTR).

IIM automatically gathers the full incident context the moment an alert fires, runs it through an
**AI layer that reasons about the root cause** (connecting an error spike to a recent deploy/change),
and presents everything on a **single pane of glass**. On-call sees a summary, a root-cause hypothesis
with evidence, and a recommended action in one place, in under a minute.

## 2. Goals (Phase-1 product scope)

1. Ingest alerts from AWS (CloudWatch Alarm / Logs Metric Filter) and gather context **read-only**.
2. AI analysis layer producing structured JSON: `severity`, `summary`, `root_cause`,
   `recommended_action`, `confidence` (already implemented in `ai/analyze_incident.py`).
3. A board showing the incident + gathered context + AI analysis (single pane of glass).
4. Create an Azure DevOps ticket (**one-way**) for serious incidents.
5. Cache-first + dedup to save tokens and avoid re-analyzing the same incident.
6. Run **end-to-end for exactly one demo service** (`GCM`) on a self-built sandbox.

## 3. Non-goals (out of scope — "future potential" slide only)

- ❌ Multi-cloud / Azure collector. *Design the interface only; do not build a second collector.*
- ❌ Auto-remediation / auto-executing actions. IIM only **recommends** to a human.
- ❌ Anomaly detection / predictive ML.
- ❌ Supporting multiple services. One service proves the concept.
- ❌ Two-way sync with Azure DevOps. One-way create + comment is enough.
- ❌ Complex dedup optimization. A simple fingerprint is enough.
- ❌ User auth / board access control. Internal prototype.

> **Scope guardrail.** Scoring rubric: Real value 35% · Effective AI use 25% · Completeness 20% ·
> Creativity 10% · Future potential 10%. The first two (60%) are where the spec stays focused. Anything
> that only serves "future potential" is slide material, not build scope.

## 4. Scope boundary

- **One service:** `GCM` (exact ECS service name + log group — see [OPEN_QUESTIONS.md](./OPEN_QUESTIONS.md)).
- **Self-built sandbox** with fake/anonymized data. No real customer data at any point.
- **Region:** `ap-southeast-1`.
- Primary incident type demonstrated end-to-end: **infrastructure** (OOM / 5xx). A second,
  **non-infrastructure** type (third-party API cost overage) is already supported by the AI layer
  (`ai/samples/apicost_overage.json`) and demonstrates flexibility, but is not wired to a live trigger
  in Phase 1.

## 5. Success metrics (for the final slide)

- **MTTR before/after:** time to *understand* an incident manually (jumping between tools) vs. via IIM.
  Illustrative target: **~15 minutes → under 1 minute**.
- **Cost:** near-zero idle infrastructure + a few to a few tens of USD/month for the LLM, versus an
  observability platform costing thousands/month.

## 6. Acceptance criteria (Phase-1 "done")

The phase is demonstrable when all of the following hold on the sandbox:

- **AC1 — Trigger:** pressing the sandbox "break it" control (OOM or 5xx) fires a CloudWatch alarm that
  reaches the analyzer with no manual step.
- **AC2 — Context:** the analyzer gathers real, read-only context for `GCM` (ECS status, ALB target
  health, sample logs filtered by `level`, metrics, most recent deploy).
- **AC3 — Analysis:** the AI layer returns a valid 5-field JSON analysis grounded only in the provided
  context (no hallucinated services/metrics), connecting the anomaly to the recent deploy where relevant.
- **AC4 — Board:** the incident, its context, and the AI analysis appear on the board (single pane) within
  ~1 minute of the trigger.
- **AC5 — Ticket:** a serious (AI `severity = critical`) incident auto-creates exactly one Azure DevOps
  Bug; a recurrence of the same fingerprint adds a comment instead of a duplicate.
- **AC6 — Cache:** a recurring incident within the TTL window returns from the DynamoDB cache with a
  visible speed difference and no new LLM call.
- **AC7 — Cost guardrails:** the LLM is invoked only for CRITICAL-class triggers; an AWS budget alert is
  configured before anything runs continuously.

## 7. Hard constraints

- **Secrets:** never commit secrets (Azure DevOps PAT, AWS keys, tokens). Use AWS Secrets Manager or env
  vars. `.gitignore` already blocks the sensitive paths.
- **No real data:** sandbox only, with fake/anonymized data (competition rule).
- **Low cost:** prefer serverless (nothing running 24/7); test locally first, deploy to AWS last; set an
  AWS budget alert when touching AWS; call the LLM only for CRITICAL / threshold-breaching incidents; keep
  LLM input compact; cache + dedup to avoid duplicate calls.
- **IAM read-only:** the context-gathering Lambda uses only `Describe*`, `Get*`, and `logs:StartQuery` /
  `logs:GetQueryResults`. It never mutates infrastructure.
- **Clean collector abstraction:** context gathering sits behind a shared interface so a second cloud is
  "just write a new collector" later (Phase 1 is AWS-only).

## 8. Existing assets (do not recreate or rewrite)

- `ai/analyze_incident.py` — `SYSTEM_PROMPT` (anti-hallucination analysis prompt), `build_user_message()`
  (compact context assembly; prints only present fields → handles both infra and non-infra incidents),
  `fingerprint()` (service + normalized error signature + deploy version), and `analyze()` (cache-first,
  calls Bedrock, parses JSON). The in-memory cache is replaced by DynamoDB + TTL in Step 4. **Reuse
  `analyze()` in Step 1 — do not write a new prompt or analysis logic.**
- `ai/samples/infra_oom.json`, `ai/samples/apicost_overage.json` — anonymized test contexts.
- `README.md`, `.gitignore` — already exist.
