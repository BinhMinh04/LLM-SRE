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
  docker compose up db backend
  # sanity check:
  curl localhost:8000/healthz     # -> {"status":"ok", ...}
  ```

  Incident analysis calls an LLM, so the backend needs credentials for its configured provider
  (AWS Bedrock by default; set `LLM_PROVIDER=deepseek` + `DEEPSEEK_API_KEY` in a root-level `.env` to
  test without AWS). The read paths (listing/opening existing incidents, document ingest + list) work
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

### Or: the whole stack in Docker, from the repo root

No need to `cd` into `backend/` or `frontend/` — one command builds and runs all three services:

```bash
docker compose up --build   # db + backend :8000 + frontend :5173
```

The frontend image (`frontend/Dockerfile`) builds the Vite bundle with Node, then serves it with nginx,
which reverse-proxies `/api` and `/healthz` to the `backend` service (`frontend/nginx.conf`) — the same
relative-API pattern as the dev proxy above. This build has **no hot reload**; keep using `npm run dev`
while actively changing frontend code, and reach for `up --build` for full-stack smoke-testing or demos.

### Other scripts

```bash
npm run build      # type-check (tsc -b) + production build to dist/
npm run preview    # serve the production build locally
npm run typecheck  # type-check only
```

## What you can do

- **Dashboard** (Overview) — 4 stat cards (active incidents, needs attention, knowledge docs, AI
  analyses), a **Recent incidents** list (click one to open it in the Incidents view), and an
  **Activity** feed built from real events (incidents ingested, documents indexed) — no fabricated
  activity.
- **Incidents** — a two-pane list + detail. **New incident** ingests a context JSON (with
  `infra_oom` / `apicost_overage` presets); the detail panel shows the AI analysis, evidence chunks,
  raw context, and the cache HIT/MISS state. Re-submitting the same incident demonstrates a cache HIT.
- **Knowledge Base** — document cards; **New document** ingests a runbook / postmortem / etc. so it
  becomes retrievable evidence for analysis.
- **Search** — the top bar's search box filters incidents (by service/summary/status/fingerprint) and
  documents (by title/service/source type/tags) live as you type, across the Dashboard, Incidents, and
  Knowledge Base views.
- **Notification bell** — badges with the count of incidents needing attention (Critical/High severity);
  clicking it jumps to Incidents.
- **Theme** — light/dark toggle in the top bar (persisted to `localStorage`). The navigation rail stays
  dark in both themes by design.
- **Designed loading / empty / error states** — every list shows a shimmer skeleton while loading, an
  inviting empty state when there's nothing yet, and — if the backend is unreachable — a state that
  explains the fix (the `docker compose … up` command above) with a **Retry** button, instead of a bare
  error string.

## Layout

```
src/
  lib/          api client (+ errText), DTO types, theme, severity/status mapping,
                 format helpers, nav config, useDashboard (shared incidents+docs fetch)
  components/   layout/ (Sidebar, TopBar, PageHeader) + ui/ (hand-rolled primitives:
                 Button, Card, Badge, SeverityBadge, StatusBadge, StatTile, Modal,
                 Skeleton, EmptyState, ErrorState) + ActivityFeed
  pages/        Overview (dashboard), Incidents, KnowledgeBase
  features/     incidents/ and documents/ workflows (lists, detail, ingest modals)
```

`src/lib/types.ts` mirrors the backend DTOs and is the source of truth for request/response shapes —
when the backend adds a field, update it there (plus the relevant page/feature) to render it.

## Design language

A light SaaS incident-dashboard look with a **permanently-dark navigation rail** — the rail's CSS
variables in `src/index.css` are not theme-flipped, so it stays dark in both light and dark mode.
Indigo accent (`--accent`), pastel severity/status pills (always paired with a text label — never color
alone), soft rounded cards with a gentle hover lift, and an ambient `.plane-aurora` gradient wash behind
the content. Fonts: **Plus Jakarta Sans** (display), **Inter** (body), **JetBrains Mono** (data/ids).

Components reference role tokens (`bg-surface`, `text-ink`, `--sev-critical`, `--rail-*`) rather than
raw hex, so the theme swaps in one place. Note: Tailwind 3.4's opacity modifiers don't compile against
CSS-variable colors (e.g. `ring-accent/25`) — use an explicit token or an arbitrary value like
`ring-[var(--accent-weak)]` instead.
