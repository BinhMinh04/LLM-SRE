# IIM Frontend — Local Test UI (MVP) — Design

**Date:** 2026-07-20
**Branch:** `feature/frontend-local` (cut from `main`, which now contains the merged RAG backend)
**Status:** Approved design, ready for implementation plan

## 1. Purpose

Provide a lean, locally-runnable web UI to exercise the existing RAG incident-analysis backend
end-to-end, so we can submit incidents, seed the knowledge base, and eyeball the AI analysis +
retrieved evidence quickly and iterate. This is an MVP test harness, **not** the polished M4 board.
It deliberately stops short of the full SPEC M4 scope (SSE streaming, auth, polish, S3 deploy).

## 2. Non-goals (YAGNI)

- SSE / token streaming (backend `/api/incidents/{id}/stream` and `/api/stream` are not implemented).
- Auth / sessions.
- Visual polish, theming, animations.
- Full `shadcn/ui` install (generator + Radix). We hand-roll a few small components instead.
- Automated frontend tests.
- Production build / S3 / CloudFront deploy, docker `frontend` service.

These are explicitly deferred to the M4 board in `.claude/specs/SPEC.md`.

## 3. Backend it talks to (already on `main`)

FastAPI, CORS enabled, base `http://localhost:8000`. REST endpoints consumed:

| Method | Path | Use |
|---|---|---|
| `GET`  | `/healthz` | header status dot (`ok` / `degraded`) |
| `POST` | `/api/incidents` | ingest + analyze one incident (synchronous — analysis is persisted before the response returns) |
| `GET`  | `/api/incidents` | list incidents (newest first; optional `service` / `severity` / `status` filters) |
| `GET`  | `/api/incidents/{id}` | one incident: context + analysis + evidence chunks |
| `POST` | `/api/documents` | ingest one knowledge doc (chunk + embed + store) |
| `GET`  | `/api/documents` | list indexed documents |

**Key contracts (from backend DTOs):**

- `POST /api/incidents` body: `{ "source": "manual|auto|webhook", "context": { ...; service required } }`
  → `201 { incident_id, status, stream }`. `422` if `context.service` missing.
- `GET /api/incidents/{id}` → `IncidentDetail`: `{ id, service, source, status, fingerprint, context,
  created_at, updated_at, analysis }` where `analysis` (`AnalysisOut`) =
  `{ severity, summary, root_cause, recommended_action, confidence, model_id, _cache: "HIT"|"MISS",
  evidence: [ { chunk_id, source_type, title } ] }`.
- `POST /api/documents` body: `{ title, source_type: "runbook|postmortem|architecture|vendor",
  service?, tags: [], content }` → `201 { document_id, chunks }`. `422` on bad `source_type` / empty content.
- `GET /api/documents` → `DocumentSummary[]`:
  `{ id, title, source_type, service, tags, chunk_count, created_at, updated_at }`.

**Flow note:** because ingest is synchronous, the "create incident" flow is `POST /api/incidents`
→ take `incident_id` → `GET /api/incidents/{id}` to render analysis + evidence. No polling; the
`stream` field is ignored for now.

## 4. Stack & layout

- **Location:** new `frontend/` at repo root.
- **Stack:** Vite + React + TypeScript + Tailwind CSS. No shadcn generator; hand-rolled UI primitives
  (`Button`, `Card`, `Badge`, `Field`, `Textarea`, `Modal`) under `src/components/ui/`.
- **Routing:** single board page at `/`. The detail view is a right-hand panel in the same page, not a
  separate route. (React Router optional — a single page needs none; skip it unless a second route appears.)
- **Dev networking:** Vite dev server on `:5173` with a proxy `/api` → `http://localhost:8000`. The
  API base is `/api` so the same code would work behind a reverse proxy later. CORS is already enabled
  on the backend as a fallback.

**Two-column board:**

```
┌─ Incidents (left) ───┐  ┌─ Detail (right) ─────────────────┐
│ [+ New incident]     │  │ severity badge · summary          │
│ [+ New document]     │  │ root_cause                        │
│ tabs: Incidents|Docs │  │ recommended_action                │
│ ── list rows ──      │  │ confidence · model_id · _cache    │
│  service             │  │ ── Evidence chunks ──             │
│  severity · status   │  │  [source_type] doc title          │
│  created_at          │  │ ── Context (JSON, collapsible) ── │
└──────────────────────┘  └───────────────────────────────────┘
```

Selecting a row fetches `GET /api/incidents/{id}` and fills the right panel. The Docs tab lists
documents from `GET /api/documents`.

## 5. Components / modules (each has one clear job)

- `src/lib/types.ts` — TypeScript types mirroring the backend DTOs (section 3).
- `src/lib/api.ts` — thin `fetch` wrapper: JSON in/out, throws a typed error carrying HTTP status +
  backend `detail` string so the UI can show `422` validation messages verbatim.
- `src/components/ui/*` — presentational primitives (Button, Card, Badge, Field, Textarea, Modal).
- `src/features/incidents/IncidentList.tsx` — left list + row selection.
- `src/features/incidents/IncidentDetail.tsx` — right panel (analysis + evidence + context).
- `src/features/incidents/NewIncidentModal.tsx` — `source` select, JSON `context` textarea, two preset
  buttons (`infra_oom`, `apicost_overage`) loading the sample payloads from `backend/tests/samples/`
  (inlined as constants so the FE has no filesystem dependency), submit → create → auto-open detail.
- `src/features/documents/DocumentList.tsx` — Docs tab list.
- `src/features/documents/NewDocumentModal.tsx` — title / source_type / service / tags / content form.
- `src/components/HealthDot.tsx` — polls `/healthz` for the header status.
- `src/App.tsx` — layout, tab state, selection state, wires the pieces.

## 6. Data flow

1. On load: `GET /api/incidents` → left list; `GET /healthz` → header dot.
2. New incident: modal → `POST /api/incidents` → on `201`, `GET /api/incidents/{id}` → render detail,
   refresh list. Re-submitting an identical incident shows `_cache: HIT` in the detail — a built-in
   way to demonstrate the cache.
3. New document: modal → `POST /api/documents` → toast `{document_id, chunks}`, refresh Docs tab.
4. Row click: `GET /api/incidents/{id}` → detail panel.

## 7. Error handling

- Network / non-2xx: `api.ts` throws `ApiError { status, detail }`. Modals show `422` `detail` inline;
  a top-level toast shows unexpected errors. No silent failures.
- Empty states: "No incidents yet — create one." / "No documents indexed."
- Backend down: header dot goes `degraded`/offline; list shows a retry.

## 8. Running locally

```bash
# 1) backend + db
docker compose up db backend                       # db (pgvector) + backend on :8000
#    (or: cd backend && uv sync && uv run uvicorn app.main:app --reload)

# 2) frontend
cd frontend && npm install && npm run dev           # Vite on :5173, proxies /api -> :8000
```

## 9. Acceptance criteria

- `npm run dev` serves the board at `:5173`; header dot reflects `/healthz`.
- Can create an incident by pasting JSON or loading a preset; the detail panel then shows severity,
  summary, root_cause, recommended_action, confidence, model_id, cache state, and evidence chunks.
- Re-submitting the same incident shows `_cache: HIT`.
- Can ingest a knowledge document and see it appear in the Docs tab with a chunk count.
- `422` validation errors from the backend are surfaced in the UI, not swallowed.
- No console errors on the happy path.

## 10. Open items (decide during planning, low-risk)

- Whether to add optional list filters (service/severity/status) now or defer — leaning defer.
- Evidence rows are `{ chunk_id, source_type, title }` (no snippet/score yet). The detail panel shows
  a `source_type` badge + document `title` per row; snippet display waits until the backend returns chunk text.
