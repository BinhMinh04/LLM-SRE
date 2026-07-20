# IIM Frontend — Local Test UI

A **Vite + React + TypeScript + Tailwind** single-page app for exercising the IIM backend end-to-end
on your machine: submit incidents, seed the knowledge base, and inspect the AI analysis together with
the evidence chunks it cited.

This is a **local test/development UI**, not the production board. It is intentionally lean — no SSE
streaming, no auth, no automated tests. See `.claude/specs/FRONTEND_LOCAL.md` (design) and
`.claude/specs/FRONTEND_LOCAL_PLAN.md` (task breakdown) for the full write-up.

## Prerequisites

- **Node ≥ 18** (Vite 5).
- The **backend running on `:8000`** (it lives in `backend/`, on `main`). The quickest way:

  ```bash
  # from the repo root — Postgres (pgvector) + FastAPI backend:
  docker compose -f infra/docker-compose.yml up
  # sanity check:
  curl localhost:8000/healthz     # -> {"status":"ok", ...}
  ```

  Incident analysis calls an LLM, so the backend needs credentials for its configured provider
  (AWS Bedrock by default; set `LLM_PROVIDER=deepseek` + `DEEPSEEK_API_KEY` in `infra/.env` to test
  without AWS). The read paths (listing/opening existing incidents, document ingest + list) work
  without a live LLM.

## Run

```bash
cd frontend
npm install
npm run dev        # Vite dev server on http://localhost:5173
```

Open **http://localhost:5173**. The dev server proxies `/api` and `/healthz` to `:8000` (see
`vite.config.ts`), so the app uses a relative API base and needs no CORS setup. The header status pill
reflects `/healthz` — it turns red if the backend is unreachable.

### Other scripts

```bash
npm run build      # type-check (tsc -b) + production build to dist/
npm run preview    # serve the production build locally
npm run typecheck  # type-check only
```

## What you can do

- **Overview** — stat tiles, a severity breakdown, and recent incidents (click one to open it).
- **Incidents** — a two-pane list + detail. **New incident** ingests a context JSON (with
  `infra_oom` / `apicost_overage` presets); the detail panel shows the AI analysis, evidence chunks,
  raw context, and the cache HIT/MISS state. Re-submitting the same incident demonstrates a cache HIT.
- **Knowledge Base** — document cards; **New document** ingests a runbook / postmortem / etc. so it
  becomes retrievable evidence for analysis.
- **Theme** — light/dark toggle in the top bar (persisted to `localStorage`).

## Layout

```
src/
  lib/          api client, DTO types, theme, severity mapping, nav config
  components/   layout/ (Sidebar, TopBar) + ui/ (hand-rolled primitives)
  pages/        Overview, Incidents, KnowledgeBase
  features/     incidents/ and documents/ workflows (lists, detail, ingest modals)
```

`src/lib/types.ts` mirrors the backend DTOs and is the source of truth for request/response shapes —
when the backend adds a field, update it there (plus the relevant page/feature) to render it.

Design tokens (light/dark surfaces, severity colors) are CSS variables in `src/index.css`; components
reference roles (`bg-surface`, `text-ink`, `--sev-critical`) rather than raw hex, so the theme swaps in
one place.
