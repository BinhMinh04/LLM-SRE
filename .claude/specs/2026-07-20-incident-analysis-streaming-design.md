# Incident Analysis Streaming (SSE) — Design

**Date:** 2026-07-20
**Status:** Approved, ready for planning
**Scope:** Backend (async ingest + SSE endpoint + event bus) and frontend (live progress UI).

## Problem

`POST /api/incidents` currently runs the whole analysis synchronously — it awaits the
LangGraph analyzer (triage → retrieve → diagnose → critic → synthesize, or the single-pass
RAG analyzer, depending on `analysis_mode`) and only returns once `status == "analyzed"`. The
response already advertises `stream: "/api/incidents/{id}/stream"`, but that route does not
exist. The frontend has no way to show progress while an incident is being analyzed; the
"New incident" button sits on "Analyzing…" until the whole pipeline finishes.

## Goals

- POST returns immediately with `status: "analyzing"`; analysis runs in the background.
- A real `GET /api/incidents/{id}/stream` SSE endpoint emits per-stage progress and a final
  result (or failure).
- The frontend shows a live timeline of analysis stages, then swaps to the result view.
- A failed analysis lands in a clear `failed` state instead of hanging on `analyzing`.

## Non-goals

- Token-by-token LLM streaming (stages only — LLM calls stay non-streaming).
- Durable event history / replay across backend restarts (in-memory only; a restart mid-analysis
  surfaces as `failed`, see below).
- Multi-worker / horizontally-scaled delivery (the app is a single-process local dev/test tool).
- Auth on the stream endpoint (a separate sub-project follows this one).

## Approach

In-process pub/sub with a per-incident `asyncio.Queue`, chosen over a Postgres
`incident_events` table or `LISTEN/NOTIFY` because the app runs as one `uvicorn` process and
does not need cross-restart durability or multi-worker fan-out. The extra machinery of a DB
table or Postgres notifications would be over-engineering for a single-instance dev tool.

## Architecture / data flow

```
POST /api/incidents
  → create Incident (status="analyzing"), commit, return { incident_id, status, stream }
  → asyncio.create_task(run_analysis(incident_id, source, context))
       ↳ opens its OWN session/UnitOfWork (request session is already closed)
       ↳ runs the remaining analyze + persist, passing a ProgressReporter into the analyzer
       ↳ each node publishes a `stage` event to the bus
       ↳ on success: set_status("analyzed"), commit, publish `analyzed` (full detail), close
       ↳ on error:   set_status("failed"),   commit, publish `failed`  ({message}),    close

GET /api/incidents/{id}/stream
  → if incident is already analyzed/failed at subscribe time:
        emit one snapshot event (read fresh from DB) and close immediately
  → else subscribe to the bus queue for this incident:
        yield an SSE line per event until the terminal event, then close
  → if incident is "analyzing" but no queue exists (e.g. backend restarted mid-run):
        emit `failed` with message "analysis interrupted" so the client never hangs
```

The only new seams are one domain port (`ProgressReporter`) and one infrastructure component
(`IncidentEventBus` + the SSE endpoint). Repositories and other domain entities are unchanged.

## Components

### `IncidentEventBus` (infrastructure)

- Singleton held on `app.state` (module-level accessor for tasks/endpoints).
- `dict[incident_id, asyncio.Queue]`.
- `open(incident_id)` — create a queue when a background analysis starts.
- `publish(incident_id, event)` — enqueue an event (no-op if no subscriber queue; the endpoint
  falls back to a DB snapshot, so a missed live event never loses the final result).
- `subscribe(incident_id)` — async generator yielding events until a terminal event.
- `close(incident_id)` — drop the queue after the terminal event (small grace so a just-attached
  subscriber drains it). The bus serves the *live* path only; terminal snapshots read from DB.

### `ProgressReporter` port (domain)

```python
class ProgressReporter(Protocol):
    async def stage(self, name: str, detail: str | None = None) -> None: ...
```

- `NullReporter` — no-op default, so existing tests and the dev/debug harness need no changes.
- `GraphAnalyzer.analyze()` and `RagAnalyzer.analyze()` gain an optional `reporter` param and
  call `await reporter.stage(...)` at each node. The cache-HIT path emits `stage("cached")`.
- `IngestIncident` receives a `reporter` and passes it to the analyzer; it stays free of any
  SSE/framework knowledge.

### Background task (`run_analysis`)

- Scheduled from the POST handler via `asyncio.create_task`.
- Opens a fresh session/UoW (the request's session is closed by the time it runs).
- Wraps the analyze+persist in try/except: success → `analyzed`; exception → `failed` + publish
  `failed`. Always closes the bus channel in a `finally`.

## Event contract (SSE)

Each message: an `event:` type and a `data:` JSON payload.

| event      | data                                   | emitted when                                                        |
|------------|----------------------------------------|---------------------------------------------------------------------|
| `stage`    | `{ stage, label, detail? }`            | entering a node: `triage`/`retrieve`/`diagnose`/`critic`/`synthesize`; `retrieve` includes `detail: "6 evidence chunks"`; cache hit emits `stage: "cached"` |
| `analyzed` | full `IncidentDetail` (same as GET)    | analysis finished                                                   |
| `failed`   | `{ message }`                          | analyzer raised, or analysis was interrupted by a restart           |

Reconnect / late-subscribe (per approved decision): the endpoint always sends the current state.
If already terminal, it emits the matching terminal event (read fresh from DB for `analyzed`) and
closes. If `analyzing` with no live queue, it emits `failed` ("analysis interrupted").

**Ordering (avoid a TOCTOU race):** the endpoint must subscribe to the bus queue *before* it
reads incident status from the DB. Otherwise a "read status == analyzing" followed by "subscribe"
can straddle the moment the background task publishes the terminal event and closes the queue —
the client would then see no queue and wrongly emit `failed` ("interrupted") for an incident that
actually succeeded. Concretely: (1) attach to the bus (creating the queue if absent), (2) re-read
status from DB; if already terminal, emit the DB snapshot and close; (3) else stream from the
queue. The background task keeps the queue alive for a short grace period after the terminal event
so a subscriber that attached in step (1) still drains it.

## Error handling

- Add `"failed"` to the `Incident` status set: `new | analyzing | analyzed | failed | ticketed |
  resolved`. The DB `status` column is `Text` with no enum constraint, so **no migration** is
  required — this is an application-level value only.
- `run_analysis` on exception: `set_status("failed")`, commit, `bus.publish(failed, {message})`.
- Frontend: `failed` renders a compact `ErrorState` in the detail panel with a Retry action that
  re-POSTs the same context.

## Frontend

- `src/lib/useIncidentStream.ts` — hook that opens `EventSource('/api/incidents/{id}/stream')`,
  returns `{ stages, result, error, done }`, and closes on `analyzed`/`failed`.
- `IncidentDetail` — when `status === "analyzing"`, render a live stage timeline in the
  `ActivityFeed` visual style (rail-agnostic, pastel, matches the design language). When `result`
  arrives, render the existing result view. `failed` → `ErrorState` + Retry.
- `NewIncidentModal` — on submit, close the modal immediately and open the (still `analyzing`)
  incident so the user watches the stream, instead of the button hanging on "Analyzing…".
- `nginx.conf` — disable proxy buffering for the stream path (`proxy_buffering off;`) so SSE is
  not buffered in the Docker/nginx path. Vite's dev proxy already forwards `/api`.
- `src/lib/types.ts` — add the SSE event payload types; add `"failed"` to the incident status
  union used by `status.ts` badges.

## Testing

- POST returns `status: "analyzing"` immediately (update the existing `test_incidents_http.py`
  assertion that currently expects `"analyzed"`).
- SSE endpoint with a fake analyzer that emits a few stages: assert the client reads the `stage`
  events followed by `analyzed`.
- Failure branch: fake analyzer raises → assert incident ends `failed` and the stream emits
  `failed`.
- `IncidentEventBus` unit tests: open / publish / subscribe / close, and the no-subscriber and
  no-queue (interrupted) fallbacks.

## Delivery (one commit per vertical slice, all on `feature/incident-analysis-streaming`)

1. `IncidentEventBus` + `ProgressReporter` port + `NullReporter`, with unit tests.
2. Async POST + `run_analysis` background task + `GET /.../stream` SSE endpoint + `failed` status;
   update backend tests.
3. Frontend: `useIncidentStream`, `IncidentDetail` live timeline, `NewIncidentModal` flow,
   `nginx.conf`, types.

Each commit builds and is independently reviewable.
