# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**LLM-SRE** (internal name **IIM**) is an AI incident-analysis layer for SRE / on-call work. It feeds an
automatically-collected incident context bundle into an LLM (AWS Bedrock, Claude models) and returns a
structured triage analysis as JSON: `severity`, `summary`, `root_cause`, `recommended_action`, `confidence`.

The project is being built in numbered steps. Only **Step 0** exists today: `backend/ai/analyze_incident.py`, a
standalone CLI that needs no AWS infrastructure other than Bedrock access. Later steps (referenced in code
and `.gitignore` but **not yet built**) add persistence and a UI — see Roadmap below. Do not assume that
infrastructure exists; check before referencing it.

## Running

In the target architecture the analysis brain is **not run by hand** — the backend app (FastAPI)
imports it as a library and invokes it through the LangGraph multi-agent graph when an incident is
ingested (`POST /api/incidents`). The app is the entry point:

```bash
# Full stack — db (pgvector) + backend (FastAPI) + frontend (nginx static build).
# Run from the repo root; no need to cd into backend/ or frontend/ first:
docker compose -f iac/docker-compose.yml up --build
# backend only, for development:
cd backend && uv sync && uv run uvicorn app.main:app --reload
```

Until that backend exists, the Step 0 brain can be exercised directly on a sample — a **dev/debug
harness only**, not how the app runs in production:

```bash
pip install boto3
export AWS_REGION=ap-southeast-1        # account/role must have Bedrock access to the model
python backend/ai/analyze_incident.py backend/ai/samples/infra_oom.json        # infrastructure (OOM/5xx)
python backend/ai/analyze_incident.py backend/ai/samples/apicost_overage.json  # non-infrastructure (API cost)
```

Running a sample calls the LLM once (cache miss), then re-runs the same incident to demonstrate a cache
hit (0 tokens). There is no test suite yet (`.gitignore` anticipates `pytest`).

- **Model / region**: set in constants at the top of `analyze_incident.py` (`MODEL_ID`, `REGION`). Defaults
  to a Haiku model for cost. Region `ap-southeast-1` may require a Bedrock *inference profile* prefix
  (e.g. `apac.anthropic.claude-...`) rather than the bare model id — confirm against the Bedrock console
  (Model access) if a call fails.

## Frontend (`frontend/` — local test UI)

A **Vite + React + TypeScript + Tailwind** single-page app that exercises the backend REST API
end-to-end: submit incidents, seed knowledge documents, and view the AI analysis plus the evidence
chunks it cited. It is a **local test/development UI** for iterating on the pipeline — deliberately
lean (no SSE streaming, no auth, no automated tests). Full design and task breakdown live in
`.claude/specs/FRONTEND_LOCAL.md` and `.claude/specs/FRONTEND_LOCAL_PLAN.md`; run instructions are in
`frontend/README.md`.

```bash
# Option A — full stack in Docker, from the repo root (no cd needed):
docker compose -f iac/docker-compose.yml up --build     # db + backend :8000 + frontend :5173

# Option B — frontend with hot reload, backend still via Docker:
docker compose -f iac/docker-compose.yml up db backend  # db (pgvector) + backend on :8000
cd frontend && npm install && npm run dev               # Vite on :5173, proxies /api -> :8000
```

Open **http://localhost:5173**. In dev mode, Vite proxies `/api` and `/healthz` to `:8000`
(`vite.config.ts`); the Docker image serves the production build via nginx, which proxies the same two
paths to the `backend` service (`frontend/nginx.conf`) — either way the app talks to a relative base and
needs no CORS config. The Docker image has no HMR, so keep using `npm run dev` (Option B) while actively
changing frontend code; `up --build` is for full-stack smoke-testing or demos. Structure:

- **`src/lib/`** — `api.ts` (thin fetch wrapper; throws `ApiError` carrying the backend `detail`, plus
  `errText()` to normalize any thrown value — network `TypeError`, non-JSON proxy error page, or
  `ApiError` — into one display string), `types.ts` (mirrors the backend DTOs — the source of truth for
  request/response shapes), `theme.ts` (light/dark), `severity.ts` (severity → fixed status palette),
  `status.ts` (incident lifecycle status → pastel badge tone), `format.ts` (`timeAgo`, `incidentRef`),
  `nav.ts` (sidebar sections + the three views), `useDashboard.ts` (one shared fetch of incidents +
  documents, keyed by a `refreshKey` the App bumps after any ingest — Overview, Incidents, and the top
  bar's alert count all read from this single hook so they never disagree).
- **`src/components/`** — `layout/` (`Sidebar` — dark nav rail with sectioned nav; `TopBar` — search,
  notification bell keyed off urgent-incident count, health pill, theme toggle; `PageHeader` — per-view
  title + primary action) and `ui/` (hand-rolled primitives: Button, Card, Badge, SeverityBadge,
  StatusBadge, StatTile, Modal, `Skeleton` (loading shimmer), `EmptyState`, `ErrorState` (the designed
  "can't reach the backend" screen — shows the fix command + Retry), …) plus `ActivityFeed` (a real
  timeline built from incident-ingested / document-indexed events, not fabricated activity). No
  component library.
- **`src/pages/`** — `Overview` (stat cards + recent incidents + activity feed dashboard), `Incidents`
  (list + detail two-pane), `KnowledgeBase` (document cards). All three take the shared `useDashboard`
  data plus the top bar's search query and render loading/empty/error states explicitly.
- **`src/features/`** — the incident and document workflows (lists, detail, ingest modals).
- **`Dockerfile` / `nginx.conf`** — multi-stage build (Node build → nginx serve) for the Docker Compose
  path above; not used by `npm run dev`.

**Design language**: a light SaaS dashboard with a **permanently-dark navigation rail** (the rail tokens
in `src/index.css` are never theme-flipped — it stays dark in both light and dark mode). Indigo accent,
pastel status/severity pills (always color *and* text label, never color alone), soft rounded cards, an
ambient `.plane-aurora` gradient wash behind the content plane. Fonts: Plus Jakarta Sans (display),
Inter (body), JetBrains Mono (data/ids). Tokens are CSS variables in `src/index.css`; components
reference roles (`bg-surface`, `text-ink`, `--sev-critical`, `--rail-*`) rather than raw hex, so theming
swaps in one place. Tailwind 3.4 caveat: opacity modifiers on CSS-var colors (`ring-accent/25`) don't
compile — use an explicit token or an arbitrary value (`ring-[var(--accent-weak)]`) instead. When the
backend adds a field, update `src/lib/types.ts` (and the relevant page/feature) to render it — keep it
in sync with the DTOs.

## Architecture (`backend/ai/analyze_incident.py`)

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
`backend/ai/samples/` are the canonical examples of the two supported shapes:

- **Infrastructure** (`infra_oom.json`): `ecs`, `alb`, `metrics`, `sample_logs`, `recent_deploy`.
- **Non-infrastructure** (`apicost_overage.json`): `alert` (human description) plus `metrics` / `sample_logs`.

When extending the input format, update `build_user_message()` to render the new field and keep the samples
in sync as living documentation.

## Git workflow

`main` is protected. Never commit or push directly to `main` — always work on a branch and land changes via
PR. **Before starting any code change, explicitly create a branch named `<type>/<short-kebab-slug>`**
matching the task, using the type that fits:

| Prefix | Use for |
|---|---|
| `feature/<slug>` | new functionality |
| `fix/<slug>` | non-urgent bug fix |
| `hotfix/<slug>` | urgent production fix |
| `chore/<slug>` | config, setup, cleanup — no behavior change |
| `refactor/<slug>` | restructuring, no behavior change |
| `docs/<slug>` | docs only |
| `test/<slug>` | tests only |

This naming is enforced by judgment (mine), not tooling — pick the type and slug from what the task
actually is. `.claude/hooks/auto-branch.sh` is only a safety net: if code gets edited while still on
`main`/`master` (e.g. a branch step was missed), it auto-creates `chore/auto-<timestamp>` so nothing lands
on `main` — that branch should be renamed or merged into the properly-named one, not used as-is.
`.claude/hooks/block-main-push.sh` denies any `git push` targeting `main`/`master` outright. Both hooks are
a backstop; the policy holds even where they can't reach (e.g. manual git outside Claude Code).

**Always pull `main` first.** Before `git checkout -b` or `git push`, pull `main` from origin — if HEAD is
on `main`, pull it directly; if on another branch, pull `main` down and merge/rebase it in before pushing
further work. Skip this only on the user's explicit say-so. `auto-branch.sh` does this itself
(`git pull --ff-only`) before cutting its fallback branch, but that only covers the one case it fires on.

**PRs**: no `Co-Authored-By` trailer on commits/PRs (`attribution.commit`/`attribution.pr` are set to `""`
in `.claude/settings.json` — don't revert this). Keep PR descriptions short: 3-4 sentences on what changed
and why, not a long Summary/Test-plan write-up.

## Roadmap (planned, not yet implemented)

Referenced by code comments and `.gitignore`, but no files exist for these yet — treat as direction, not
current state:

- **Step 4**: replace the in-memory `_CACHE` with **DynamoDB + TTL**.
- **Serverless / AWS CDK** deployment (`.serverless/`, `cdk.out/` in `.gitignore`).
- `infra/` was renamed to **`iac/`** — it will hold Terraform once infrastructure-as-code work starts
  (not written yet; today it only holds `docker-compose.yml` for local full-stack runs).

The **React frontend** now exists as `frontend/` (a local test UI — see the Frontend section above),
superseding the originally-planned `board/` location. Streaming (SSE), auth, and a polished production
board are still to come per `.claude/specs/SPEC.md`.

The full Phase-1 design (problem/goals, architecture + ADRs, DynamoDB data model, build plan, open
questions) is written up in `.claude/specs/`: `SPEC.md`, `ARCHITECTURE.md`, `DATA_MODEL.md`, `PLAN.md`,
`OPEN_QUESTIONS.md`. Read these before implementing any of the steps above — they're the source of truth
for what to build next, not this section.
