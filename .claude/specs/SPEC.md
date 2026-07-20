# IIM — Specification (Full-Stack RAG)

- **Project:** IIM (Intelligent Incident Management) — repo `LLM-SRE`
- **Date:** 2026-07-19
- **Status:** Draft (design only, no implementation yet)
- **Language:** All artifacts (code, comments, docs, UI, logs) in English.
- **Scope target:** EmeSoft Hackathon — Sprint Jul 23 – Aug 22, Demo Day Aug 28.
- **Related:** [ARCHITECTURE.md](./ARCHITECTURE.md) · [DATA_MODEL.md](./DATA_MODEL.md) ·
  [PLAN.md](./PLAN.md) · [OPEN_QUESTIONS.md](./OPEN_QUESTIONS.md)

> This spec evolves the original AWS-native serverless design into a **full-stack, self-hostable**
> build: **React (Vite) + shadcn/ui** frontend, **FastAPI + LangChain** backend, **RAG over pgvector**, run
> locally with **Docker Compose**. It **reuses the analysis brain** already implemented in
> `backend/ai/analyze_incident.py` and keeps the serverless (Lambda/DynamoDB/S3) design as a future deployment
> path — see ARCHITECTURE.md for that variant.

---

## 1. Problem

When a production incident occurs, on-call engineers jump between many tools (CloudWatch, ECS console,
log groups, deploy history) to answer two questions: **"what is on fire?"** and **"why?"**. This
context-gathering is slow and manual, which inflates Mean Time To Resolution (MTTR).

IIM gathers the full incident context the moment an alert fires, runs it through an **AI layer that
reasons about the root cause** — now **grounded in retrieved organizational knowledge (RAG)**:
runbooks, past postmortems, architecture docs, and vendor docs. It presents a summary, a root-cause
hypothesis with the exact evidence it used, and a recommended action on a **single pane of glass**, in
under a minute.

## 2. What this build adds over Step 0

Step 0 is a single Python CLI (`backend/ai/analyze_incident.py`) that turns one incident-context JSON into a
structured triage analysis via AWS Bedrock, with an in-memory cache. This spec turns that brain into a
product:

- A **FastAPI** backend exposing the analysis as an API, orchestrated with **LangChain**.
- **RAG**: before asking the LLM, retrieve the most relevant runbooks / postmortems / architecture /
  vendor docs from a **pgvector** store and inject them as grounded, cited evidence.
- **Multi-agent** orchestration (LangGraph): specialist agents retrieve per knowledge source in
  parallel, a diagnosis agent forms the root-cause hypothesis, and a critic agent verifies grounding
  and can trigger another retrieval round before the answer is finalized (corrective RAG).
- A **React (Vite) + shadcn/ui** board that lists incidents, shows context + AI analysis + the evidence
  used, and streams analysis live over **SSE**.
- **Two ingestion paths**: automatic (AWS EventBridge to collector) and manual (upload / paste JSON /
  REST from the UI) so the system is demoable without live AWS traffic.
- **SSO/OAuth** login and an **optional** one-way Azure DevOps ticket action.

### Decisions locked for this spec

| Area | Decision |
|---|---|
| LLM provider | **AWS Bedrock (Claude)** via LangChain (`langchain-aws` `ChatBedrockConverse`). Keep `MODEL_ID` / region from Step 0. |
| Embeddings | **Amazon Titan Text Embeddings v2** on Bedrock (`amazon.titan-embed-text-v2:0`, 1024-dim). Stays inside Bedrock — no new vendor. |
| Vector DB | **PostgreSQL + pgvector** (one Postgres serves both relational data and vectors). |
| RAG sources | Runbooks/SOPs, past incidents/postmortems, architecture/service docs, AWS/vendor docs. |
| Orchestration | **Multi-agent RAG** via **LangGraph** — a supervisor plus specialist retrieval agents (one per source), a diagnosis agent, and a critic agent with a corrective retrieval loop. |
| Model tiering | Cheap/mechanical agents (triage, retrievers, action, synthesize) on **Haiku**; only diagnosis + critic use the main `MODEL_ID` (Claude). |
| Ingestion | **Both** automatic (EventBridge/collector) **and** manual (UI upload / REST / webhook). |
| Realtime | **SSE** (Server-Sent Events) — one-way stream of incident updates + token streaming. |
| Auth | **SSO / OAuth** (Google or Microsoft) with JWT session. |
| Ticketing | **Optional / stretch** — one-way Azure DevOps Bug create + comment. |
| Deployment | **Docker Compose** local for the hackathon; cloud path noted but not built. |
| Backend tooling | **uv** (Astral) for Python deps + build/run — `pyproject.toml` + `uv.lock`. |

---

## 3. Goals

1. Expose incident analysis as a service: `POST` an incident context, get structured JSON back
   (`severity`, `summary`, `root_cause`, `recommended_action`, `confidence`).
2. **Ground every analysis in retrieved knowledge** (RAG) so root-cause hypotheses cite real
   runbooks / past incidents instead of relying on the model's memory.
3. Show it all on one board: incident list, per-incident context, AI analysis, and the exact evidence
   chunks the LLM used (transparency / anti-hallucination).
4. Support both automatic and manual ingestion so the system is demoable end-to-end offline.
5. Stream analysis to the UI as it is produced (SSE), with a visible cache-hit fast path.
6. Run the whole stack with a single `docker compose up`.

## 4. Non-goals (out of scope — "future potential" slide only)

- Auto-remediation / executing any change on infrastructure. IIM only **recommends** to a human.
- Multi-cloud collectors. Design the collector interface, build AWS only.
- Predictive / anomaly-detection ML.
- Two-way Azure DevOps sync. One-way create + comment only, and only if time permits.
- Production-grade cloud infra (managed Postgres, autoscaling, multi-region). Documented as a future path.
- Fine-tuning or self-hosting the LLM.

> **Scope guardrail.** Scoring rubric: Real value 35% · Effective AI use 25% · Completeness 20% ·
> Creativity 10% · Future potential 10%. The first two (60%) are where this spec stays focused. Anything
> that only serves "future potential" is slide material, not build scope.

---

## 5. Architecture

```
                          Ingestion
   AWS EventBridge/Alarm --> Collector (read-only)  -+
                                                     +--> POST /api/incidents --> FastAPI
   On-call: UI upload / paste JSON / webhook  -------+                              |
                                                                                    v
                                             +------------ Analysis pipeline (LangChain) -----------+
                                             | 1. fingerprint(ctx) -> cache lookup (Postgres)       |
                                             | 2. build query text from incident context           |
                                             | 3. embed query (Titan) -> pgvector similarity search |
                                             | 4. build_user_message(ctx) + retrieved evidence      |
                                             | 5. Bedrock converse (Claude) -> strict JSON          |
                                             | 6. persist analysis + evidence refs, tag cache       |
                                             +------------------------------------------------------+
                                                                                    |
                     SSE stream (updates + tokens)                                  v
   React board (shadcn/ui)    <-------------------------------------  FastAPI  -->  PostgreSQL + pgvector
        |                                                                            (incidents, analyses,
        +-- optional: "Create ticket" --> Azure DevOps (one-way)                      documents, chunks, cache)
```

### 5.1 Components

- **Frontend** — React SPA (Vite) + shadcn/ui + Tailwind, client-side routing (React Router). Fetches
  from FastAPI and subscribes to the SSE incident stream; built to static assets (served by nginx locally,
  S3 + CloudFront in the cloud path). Talks to FastAPI only.
- **Backend** — FastAPI (Python 3.11+). Async endpoints. LangChain orchestrates retrieval + LLM.
- **Analysis brain** — reuse `SYSTEM_PROMPT`, the strict JSON output schema, `build_user_message()`,
  and `fingerprint()` from `backend/ai/analyze_incident.py`. The Bedrock call is wrapped in LangChain instead
  of a raw boto3 `converse`. Do not rewrite the prompt or analysis logic.
- **RAG store** — pgvector extension in the same Postgres instance.
- **Collector** — a read-only AWS context gatherer (`Describe*` / `Get*` / logs queries) that posts to
  the ingestion endpoint. A thin service/script here; heavy AWS wiring stays on the roadmap.
- **Ticketing (stretch)** — a one-way client that creates an Azure DevOps Bug and comments on
  recurrences.

### 5.2 Proposed repo layout

```
iim/
  backend/                 # FastAPI + LangChain + reused Step 0 brain (uv)
    ai/                    # existing Step 0 brain (reused)
      analyze_incident.py
      samples/
    app/
      main.py              # FastAPI app, routers, CORS
      api/
        incidents.py       # ingest, list, detail, per-incident SSE
        documents.py       # RAG upload / list / reindex
        stream.py          # global SSE board feed
        auth.py            # OAuth login / callback / me
      core/
        config.py          # env settings (pydantic-settings)
        db.py              # async SQLAlchemy engine/session
        security.py        # JWT, session cookie, deps
      analysis/
        graph.py           # LangGraph state machine wiring the agents
        state.py           # shared graph state (context, queries, evidence, hypothesis, critique)
        llm.py             # ChatBedrockConverse wrappers (main + Haiku tiers, streaming)
        prompts.py         # SYSTEM_PROMPT + RAG rule + per-agent prompts, build_user_message
        agents/
          supervisor.py    # orchestrator: routing + finish/loop decision
          triage.py        # classify incident, formulate per-source retrieval queries
          retrievers.py    # runbook / postmortem / architecture / vendor retrieval agents
          diagnosis.py     # root-cause hypothesis from context + evidence
          critic.py        # verify grounding; request another retrieval round if weak
          action.py        # recommended action grounded in runbooks
          synthesize.py    # emit strict 5-field JSON + evidence refs
      rag/
        embed.py           # Titan v2 embeddings
        ingest.py          # chunk + embed + store
        retrieve.py        # pgvector similarity search
      models/              # SQLAlchemy ORM tables
      schemas/             # pydantic request/response models
    migrations/            # alembic
    pyproject.toml         # project + deps, managed by uv
    uv.lock                # pinned, reproducible lockfile (uv sync)
  frontend/                # React (Vite) + shadcn/ui SPA (new)
    index.html
    vite.config.ts
    src/
      main.tsx             # app entry + router (React Router)
      routes/
        board.tsx          # /               (incident list)
        incident.tsx       # /incidents/:id
        new-incident.tsx   # /incidents/new
        knowledge.tsx      # /knowledge
        login.tsx          # /login
      components/          # shadcn/ui-based components
      lib/                 # api client, sse hook
  iac/
    docker-compose.yml
    .env.example
```

Official docs: FastAPI https://fastapi.tiangolo.com/ · React https://react.dev/ · Vite
https://vitejs.dev/ · shadcn/ui (Vite) https://ui.shadcn.com/docs/installation/vite · LangChain (Python)
https://python.langchain.com/docs/introduction/ · LangChain AWS
https://python.langchain.com/docs/integrations/providers/aws/ · pgvector
https://github.com/pgvector/pgvector · SSE (MDN)
https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

---

## 6. Backend design (FastAPI + LangChain)

### 6.1 Multi-agent RAG pipeline (LangGraph)

Analysis is a **LangGraph** state machine, not a single LLM call. Cache-first still wraps everything: a
`fingerprint(ctx)` hit (`service | normalized-error-signature | deploy-version`, reuse Step 0 logic) in
`analysis_cache` within TTL returns instantly, tagged `_cache: HIT`, with no graph run. On a miss, the
incident flows through a supervisor and a set of specialist agents; a critic can send it back for another
retrieval round before the answer is finalized (corrective / agentic RAG). The final synthesized JSON is
persisted and its evidence chunk IDs recorded, then emitted over SSE.

```
                       cache MISS
   incident --> [supervisor] --> [triage] --> per-source retrieval queries
                                                    |
                            +-----------------------+------------------------+
                            v            v            v            v
                     [runbook]   [postmortem]  [architecture]   [vendor]     (parallel retrieval agents)
                            +-----------------------+------------------------+
                                                    v
                                             [diagnosis]  --> root-cause hypothesis + citations
                                                    v
                                              [critic] --grounded & confident?
                                                 |  no (needs more evidence, round < MAX_ROUNDS)
                                                 +----> back to triage/retrievers (reformulated queries)
                                                 |  yes
                                                 v
                                             [action] --> recommended action (runbook-grounded)
                                                 v
                                            [synthesize] --> strict 5-field JSON --> persist + SSE
```

**Shared state** (`analysis/state.py`): incident `context`, per-source `queries`, `evidence` bundles
(chunks + citations per `source_type`), `hypothesis`, `critique`, `confidence`, `round` counter, and the
final `analysis`.

**Agents / nodes**:

| Agent | Model tier | Role |
|---|---|---|
| `supervisor` | — (routing logic) | Orchestrates the graph; picks which retrievers to run for the incident shape and decides when to stop. |
| `triage` | Haiku | Classifies incident (infra vs non-infra), extracts key signals, writes one focused retrieval query per relevant `source_type`. |
| `retriever:runbook` | Haiku | Retrieves + summarizes runbook chunks for the service. |
| `retriever:postmortem` | Haiku | Finds similar past incidents and their confirmed root cause. |
| `retriever:architecture` | Haiku | Pulls dependency / blast-radius context. |
| `retriever:vendor` | Haiku | Pulls error-code / vendor-doc explanations. |
| `diagnosis` | main `MODEL_ID` (Claude) | Synthesizes context + all evidence into a root-cause hypothesis with citations. |
| `critic` | main `MODEL_ID` (Claude) | Adversarially checks grounding (no invented services/metrics, every claim cites evidence), judges confidence, and either approves or requests another retrieval round (capped at `MAX_ROUNDS`, default 2). |
| `action` | Haiku | Proposes `recommended_action`, grounded in runbook evidence. |
| `synthesize` | Haiku | Emits the strict 5-field JSON (+ `_cache`, evidence refs). |

The four retrieval agents run **in parallel** (LangGraph fan-out); each reformulates its own query and
searches `doc_chunks` filtered to its `source_type` + `service`. Only `diagnosis` and `critic` use the
stronger model — everything else runs on Haiku to keep cost down (see section 16). The critic loop is the
corrective-RAG mechanism: when evidence is too thin to conclude, it reformulates queries via `triage` and
retrieves again rather than guessing; after `MAX_ROUNDS` it must return the best-supported answer with a
lowered `confidence` and an explicit "insufficient data" note.

Official docs: LangGraph https://langchain-ai.github.io/langgraph/ · LangGraph multi-agent
https://langchain-ai.github.io/langgraph/concepts/multi_agent/

### 6.2 Prompt extension for RAG

`SYSTEM_PROMPT` from Step 0 is kept verbatim and shared by the `diagnosis` and `critic` agents; it gets
one appended rule (kept in `analysis/prompts.py`, alongside each agent's own instruction):

```
RETRIEVED KNOWLEDGE RULES:
- The user message may include a "Retrieved knowledge" section with excerpts from runbooks,
  past postmortems, architecture docs, and vendor docs.
- Treat these as reference context, not ground truth about THIS incident. Still conclude only
  from the incident data provided.
- When a conclusion is supported by a retrieved excerpt, cite it by its [source_type: title] tag.
- If retrieved knowledge conflicts with the incident data, trust the incident data and say so.
- Never invent an excerpt or a citation that is not present in the Retrieved knowledge section.
```

The "Retrieved knowledge" block is rendered as, per chunk:
`[runbook: GCM OOM Runbook #chunk-3] <chunk text>`.

### 6.3 Anti-hallucination + citations

Per analysis, the board shows exactly which retrieved chunks were fed in and (where the model provides
them) which chunk backs each conclusion. Keep the Step 0 rule set: conclude only from data, never invent
metrics/services/events, state when data is insufficient, connect timestamps (anomaly-start vs
deploy-time). RAG adds evidence; it does not relax these rules.

### 6.4 API endpoints (draft)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/incidents` | Ingest one incident context (auto or manual). Kicks off analysis. Returns `incident_id`. |
| `GET` | `/api/incidents` | List incidents (paginated; filter by service/severity/status). |
| `GET` | `/api/incidents/{id}` | Incident + context + analysis + evidence chunks used. |
| `GET` | `/api/incidents/{id}/stream` | SSE: analysis progress + streamed tokens + final result. |
| `GET` | `/api/stream` | SSE: global feed of new incidents / status changes for the board. |
| `POST` | `/api/incidents/{id}/ticket` | (Stretch) create Azure DevOps Bug one-way. |
| `POST` | `/api/documents` | Upload a knowledge doc for RAG (file or text + metadata). |
| `POST` | `/api/documents/reindex` | Re-chunk + re-embed a document or a source_type. |
| `GET` | `/api/documents` | List indexed docs (source_type, service, chunk count, updated_at). |
| `GET` | `/api/auth/login` / `/api/auth/callback` / `/api/auth/me` | OAuth login flow + session. |
| `GET` | `/healthz` | Liveness. |

All non-auth endpoints require a valid session (see Auth).

### 6.5 Example ingest request / analysis response

Request — `POST /api/incidents` (manual, infra shape; same as `backend/ai/samples/infra_oom.json`):

```json
{
  "source": "manual",
  "context": {
    "service": "GCM",
    "ecs": { "desiredCount": 3, "runningCount": 1, "events": ["service GCM has stopped 2 tasks"] },
    "alb": { "healthyHosts": 1, "unHealthyHosts": 2, "http5xx": 143 },
    "metrics": { "MemoryUtilization": 98.7, "CPUUtilization": 41.2 },
    "sample_logs": [{ "level": "ERROR", "msg": "java.lang.OutOfMemoryError: Java heap space" }],
    "recent_deploy": { "version": "1.8.0", "at": "2026-07-19T02:14:00Z" }
  }
}
```

Response:

```json
{ "incident_id": "5f2c...", "status": "analyzing", "stream": "/api/incidents/5f2c.../stream" }
```

Final analysis (persisted, also emitted as the SSE `analysis.done` event):

```json
{
  "severity": "critical",
  "summary": "GCM is returning 5xx after tasks were OOM-killed following the 1.8.0 deploy.",
  "root_cause": "Memory at 98.7% with OutOfMemoryError right after deploy 1.8.0 (02:14Z) points to a heap regression in 1.8.0. [postmortem: GCM OOM 2026-05], [runbook: GCM OOM Runbook]",
  "recommended_action": "Roll back GCM to the previous version and raise container memory; confirm task count recovers to 3.",
  "confidence": 0.82,
  "_cache": "MISS",
  "evidence": [
    { "source_type": "runbook", "title": "GCM OOM Runbook", "similarity": 0.79 },
    { "source_type": "postmortem", "title": "GCM OOM 2026-05", "similarity": 0.74 }
  ]
}
```

---

## 7. RAG design

### 7.1 Sources (all four indexed)

| `source_type` | Content | Why it helps |
|---|---|---|
| `runbook` | SOPs / operational procedures per service | "How do we handle this class of failure?" |
| `postmortem` | Past incidents + confirmed root cause + resolution | Highest value: find similar past incidents and reuse the diagnosis. |
| `architecture` | Service/dependency docs, diagrams-as-text | Reason about upstream/downstream blast radius. |
| `vendor` | AWS / third-party docs, error-code references | Explain infrastructure error signatures. |

### 7.2 Ingestion & indexing

1. Upload via `POST /api/documents` (Markdown/PDF/text + metadata: `title`, `source_type`, `service`,
   `tags`). The raw file is kept (local volume in dev, **S3** in the cloud path); chunks + embeddings go
   to Postgres.
2. **Chunk**: recursive character splitting, ~800–1000 tokens per chunk with ~100-token overlap; keep
   heading breadcrumbs in each chunk's text.
3. **Embed**: Titan Text Embeddings v2 (1024-dim) per chunk.
4. **Store** in `doc_chunks` with the embedding and metadata for filtered retrieval.
5. **Self-improving corpus**: when an incident is resolved, its context + final analysis can be written
   back as a `postmortem` document so future similar incidents retrieve it.

### 7.3 Retrieval

- Cosine similarity over `doc_chunks.embedding` (pgvector `<=>`), pre-filtered by `service` and
  optionally `source_type`. Top-K = 6 with a min-similarity threshold.
- HNSW index for fast approximate search (https://github.com/pgvector/pgvector#hnsw).

Example query (`:qvec` is the query embedding, `:svc` the service):

```sql
SELECT id, document_id, source_type, content,
       1 - (embedding <=> :qvec) AS similarity
FROM doc_chunks
WHERE service = :svc OR service IS NULL
ORDER BY embedding <=> :qvec
LIMIT 6;
```

---

## 8. Data model (PostgreSQL + pgvector)

Relational version of `.claude/specs/DATA_MODEL.md` (which is DynamoDB).

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE incidents (
  id            UUID PRIMARY KEY,
  service       TEXT NOT NULL,
  source        TEXT NOT NULL,               -- 'auto' | 'manual' | 'webhook'
  fingerprint   TEXT NOT NULL,
  context       JSONB NOT NULL,              -- the raw incident context dict
  status        TEXT NOT NULL DEFAULT 'new', -- new | analyzing | analyzed | ticketed | resolved
  created_at    TIMESTAMPTZ NOT NULL,
  updated_at    TIMESTAMPTZ NOT NULL
);
CREATE INDEX ON incidents (service);
CREATE INDEX ON incidents (fingerprint);

CREATE TABLE analyses (
  id                  UUID PRIMARY KEY,
  incident_id         UUID NOT NULL REFERENCES incidents(id),
  severity            TEXT NOT NULL,
  summary             TEXT NOT NULL,
  root_cause          TEXT NOT NULL,
  recommended_action  TEXT NOT NULL,
  confidence          NUMERIC,
  cache_state         TEXT NOT NULL,          -- HIT | MISS
  model_id            TEXT NOT NULL,
  evidence_chunk_ids  UUID[] NOT NULL DEFAULT '{}',
  created_at          TIMESTAMPTZ NOT NULL
);
CREATE INDEX ON analyses (incident_id);

CREATE TABLE analysis_cache (
  fingerprint  TEXT PRIMARY KEY,
  analysis_id  UUID NOT NULL REFERENCES analyses(id),
  expires_at   TIMESTAMPTZ NOT NULL           -- CACHE_TTL_SECONDS from now
);

CREATE TABLE documents (
  id           UUID PRIMARY KEY,
  title        TEXT NOT NULL,
  source_type  TEXT NOT NULL,                 -- runbook | postmortem | architecture | vendor
  service      TEXT,
  tags         TEXT[] DEFAULT '{}',
  created_at   TIMESTAMPTZ NOT NULL,
  updated_at   TIMESTAMPTZ NOT NULL
);

CREATE TABLE doc_chunks (
  id           UUID PRIMARY KEY,
  document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  source_type  TEXT NOT NULL,
  service      TEXT,
  chunk_index  INT NOT NULL,
  content      TEXT NOT NULL,
  embedding    vector(1024) NOT NULL
);
CREATE INDEX ON doc_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON doc_chunks (service);
CREATE INDEX ON doc_chunks (source_type);

CREATE TABLE users (
  id          UUID PRIMARY KEY,
  email       TEXT UNIQUE NOT NULL,
  name        TEXT,
  provider    TEXT NOT NULL,                  -- google | microsoft
  created_at  TIMESTAMPTZ NOT NULL
);
```

Cache expiry: a row in `analysis_cache` with `expires_at <= now()` is a miss. A different deploy version
yields a different fingerprint, forcing re-analysis after a deploy.

---

## 9. Frontend design (React + shadcn/ui)

### 9.1 Pages / routes

| Route | Purpose |
|---|---|
| `/` (Board) | Live incident list (severity chip, service, age, status). SSE-updated. |
| `/incidents/:id` | Detail: gathered context, AI analysis (5 fields), evidence chunks used, timeline (anomaly vs deploy). "Create ticket" button (stretch). |
| `/incidents/new` | Manual ingestion: paste JSON or upload a context file -> `POST /api/incidents`. |
| `/knowledge` | RAG library: upload/list/reindex documents by source_type + service. |
| `/login` | SSO/OAuth entry. |

### 9.2 Key UI behaviors

- **Live board** via a single SSE subscription; new/updated incidents animate in.
- **Streaming analysis**: on the detail page, summary + root-cause stream token-by-token during a cache
  miss; a cache hit renders instantly with a "HIT (0 tokens)" badge.
- **Evidence panel**: shows each retrieved chunk (title, source_type, similarity), making the RAG
  grounding visible — core to the anti-hallucination story.
- shadcn/ui building blocks: `card`, `badge`, `table`, `sheet`, `tabs`, `dialog`, `sonner` (toasts),
  `skeleton` for streaming placeholders.

---

## 10. Auth (SSO / OAuth)

- OAuth 2.0 / OpenID Connect with Google or Microsoft as the identity provider.
- **AWS-native option (recommended if staying all-AWS):** an **Amazon Cognito** user pool federates
  Google/Microsoft and issues the JWT directly, so the backend just validates a Cognito token instead of
  hand-rolling each provider's OAuth flow.
- Backend handles the code exchange (`/api/auth/callback`), issues an app JWT in an httpOnly cookie;
  API and SSE calls require it.
- `users` table; membership can be restricted to the `@emesoft.net` domain for the demo.
- A single dev-bypass account behind an env flag is acceptable for local dev.

Official docs: OpenID Connect https://openid.net/developers/how-connect-works/ ·
Microsoft identity platform https://learn.microsoft.com/en-us/entra/identity-platform/ ·
Google Identity https://developers.google.com/identity/protocols/oauth2

---

## 11. Realtime (SSE)

- FastAPI streams `text/event-stream`. Two channels: a per-incident stream (analysis tokens + final
  result) and a global board feed (new incident, status change).
- The browser uses `EventSource`. SSE chosen over WebSocket because traffic is one-way server->client
  and SSE auto-reconnects.

Event payload examples:

```
event: incident.created
data: {"id":"5f2c...","service":"GCM","severity":null,"status":"analyzing"}

event: analysis.delta
data: {"field":"root_cause","text":"Memory at 98.7% with"}

event: analysis.done
data: {"id":"5f2c...","severity":"critical","confidence":0.82,"cache":"MISS"}

event: incident.updated
data: {"id":"5f2c...","status":"ticketed"}
```

---

## 12. Ticketing (stretch)

- One-way only: on `severity = critical`, create a single Azure DevOps **Bug** via the REST API; a
  recurrence of the same fingerprint adds a **comment** instead of a duplicate ticket.
- PAT stored in env / secret store, never committed.
- If time runs short, ship the button + interface stub and mark it "future potential".

Official docs: Azure DevOps Work Items REST API
https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items

---

## 13. Deployment (Docker Compose)

```yaml
# iac/docker-compose.yml (sketch)
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: iim
      POSTGRES_USER: iim
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
  backend:
    build: ../backend
    environment:
      AWS_REGION: ${AWS_REGION}
      MODEL_ID: ${MODEL_ID}
      EMBED_MODEL_ID: amazon.titan-embed-text-v2:0
      FAST_MODEL_ID: ${FAST_MODEL_ID}          # Haiku tier for triage/retrievers/action/synthesize
      MAX_ROUNDS: ${MAX_ROUNDS}                 # critic corrective-retrieval loop cap (default 2)
      DATABASE_URL: postgresql+asyncpg://iim:${DB_PASSWORD}@db:5432/iim
      CACHE_TTL_SECONDS: ${CACHE_TTL_SECONDS}
      OAUTH_CLIENT_ID: ${OAUTH_CLIENT_ID}
      OAUTH_CLIENT_SECRET: ${OAUTH_CLIENT_SECRET}
    depends_on: [db]
    ports: ["8000:8000"]
  frontend:
    build: ../frontend                          # Vite build served by nginx
    environment:
      VITE_API_BASE: http://localhost:8000
    depends_on: [backend]
    ports: ["3000:80"]
volumes:
  pgdata:
```

**Backend build (uv).** The backend uses [uv](https://docs.astral.sh/uv/) for dependency management and
running; `pyproject.toml` + `uv.lock` are the source of truth (no `requirements.txt`, no `pip` in the
image). The Dockerfile builds from the official uv image and installs from the frozen lockfile:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev          # reproducible install from the lockfile
COPY . .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Local dev: `uv sync` then `uv run uvicorn app.main:app --reload`; Step 0 still runs via
`uv run python backend/ai/analyze_incident.py backend/ai/samples/infra_oom.json`. uv Docker guide:
https://docs.astral.sh/uv/guides/integration/docker/

Env vars (`.env.example`): `AWS_REGION`, `MODEL_ID`, `FAST_MODEL_ID`, `EMBED_MODEL_ID`, `MAX_ROUNDS`,
`DB_PASSWORD`, `DATABASE_URL`, `CACHE_TTL_SECONDS`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`,
`JWT_SECRET`, and (stretch) `AZDO_ORG`, `AZDO_PROJECT`, `AZDO_PAT`.

AWS credentials for Bedrock reach the backend via mounted profile or env (never committed). Cloud
production (managed Postgres, container orchestration, TLS, secrets manager) is a documented future
path, not built here.

Official docs: pgvector Docker image https://hub.docker.com/r/pgvector/pgvector ·
Amazon Bedrock Converse API
https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html ·
Titan Text Embeddings
https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html

### 13.1 AWS services (now + cloud path)

The hackathon build runs locally on Docker Compose; **Amazon Bedrock is the only hard AWS dependency**
(Claude via Converse + Titan v2 embeddings). This maps each concern to the AWS service to use, and flags
the few worth adopting even in the local build.

| Concern | Service | When |
|---|---|---|
| LLM inference + embeddings | **Amazon Bedrock** (Claude Converse, Titan v2) | Now (only hard dependency) |
| AI safety / PII filtering | **Bedrock Guardrails** | Recommended now — cheap insurance on the anti-hallucination story |
| LLM call auditing | **Bedrock model invocation logging** (to CloudWatch/S3) | Recommended now — tokens/cost per incident |
| Secrets (OAuth, Azure DevOps PAT) | **AWS Secrets Manager** (or SSM Parameter Store) | Now |
| Raw knowledge-doc storage | **Amazon S3** (originals before chunking) | Now — cheap, keeps source files |
| Auth / SSO | **Amazon Cognito** user pool, federating Google/Microsoft | Recommended — AWS-native SSO (section 10) |
| Incident source (metrics/logs/alarms) | **Amazon CloudWatch** + **EventBridge** | Cloud path (auto-collector) |
| Ingestion decoupling / dedup | **Amazon SQS** (queue incidents to an analysis worker) | Cloud path — smooths bursts, avoids duplicate graph runs |
| Vector DB (managed) | **Aurora PostgreSQL Serverless v2 + pgvector** (or RDS for PostgreSQL) | Cloud path — replaces the compose `db` |
| Backend host | **AWS App Runner** or **ECS Fargate** (container) | Cloud path — see Lambda note |
| Frontend host | **Amazon S3 + CloudFront** (static React SPA, matches ARCHITECTURE.md) | Cloud path |
| Cost guardrail | **AWS Budgets** alert | Before any continuous run |

**Why not Lambda for the backend?** The multi-agent graph has a critic loop and streams tokens over SSE;
Lambda's execution-time and streaming constraints make long, streamed, multi-call requests awkward. A
long-lived container (App Runner / Fargate) fits the LangGraph + SSE model better. The original
Lambda/DynamoDB collector still fits the read-only **ingestion** side (short, event-driven).

**Managed-RAG alternative:** **Amazon Bedrock Knowledge Bases** can do retrieval end-to-end (and can use
Aurora/pgvector or OpenSearch Serverless underneath). We deliberately keep RAG self-managed in LangGraph
so the multi-agent control (per-source retrievers, corrective critic loop, citation shaping) is explicit
rather than a black box — but Knowledge Bases is the fastest path if that control isn't needed.

Official docs: Bedrock Knowledge Bases
https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html · Bedrock Guardrails
https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html · Amazon Cognito
https://docs.aws.amazon.com/cognito/latest/developerguide/ · Aurora PostgreSQL + pgvector
https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.VectorDB.html · AWS App
Runner https://docs.aws.amazon.com/apprunner/latest/dg/ · Amazon SQS
https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/

---

## 14. Success metrics (for the final slide)

- **MTTR before/after:** time to understand an incident manually vs. via IIM. Illustrative target:
  ~15 minutes to under 1 minute.
- **Grounding quality:** every root-cause hypothesis cites at least one retrieved evidence chunk; no
  hallucinated services/metrics in the demo cases.
- **Cost:** cache-first + compact prompts + top-K retrieval keep LLM spend to a few to a few tens of
  USD/month, versus an observability platform costing thousands/month.

## 15. Acceptance criteria ("done")

- **AC1 — Ingestion:** both paths work — an automatic trigger (or the collector) and a manual UI
  upload/paste both create an incident and start analysis with no code change.
- **AC2 — Context:** the incident context is stored and rendered for both supported shapes
  (infrastructure OOM/5xx and non-infrastructure API-cost, per `backend/ai/samples/`).
- **AC3 — RAG:** retrieval returns relevant chunks filtered by service; the analysis stores the evidence
  chunk IDs actually used.
- **AC4 — Analysis:** a valid 5-field JSON analysis, grounded only in provided context + retrieved
  evidence (no hallucinated services/metrics), connecting the anomaly to the recent deploy where
  relevant.
- **AC5 — Board:** incident, context, analysis, and the evidence panel appear on the board (single pane)
  within ~1 minute of ingestion.
- **AC6 — Streaming:** on a cache miss the analysis streams token-by-token over SSE; on a cache hit it
  returns instantly with a visible "HIT (0 tokens)" badge and no new LLM call.
- **AC7 — Auth:** the board and API require SSO/OAuth login; unauthenticated requests are rejected.
- **AC8 — Ticket (stretch):** a `severity = critical` incident creates exactly one Azure DevOps Bug; a
  recurrence of the same fingerprint adds a comment instead of a duplicate.

---

## 16. Hard constraints

- **Secrets:** never commit secrets (Azure DevOps PAT, AWS keys, OAuth client secrets, tokens). Use a
  secret store or env vars. `.gitignore` already blocks the sensitive paths.
- **No real data:** sandbox / anonymized data only (competition rule). Knowledge docs for RAG must also
  be anonymized.
- **Read-only collector:** the AWS collector uses only `Describe*`, `Get*`, `logs:StartQuery` /
  `logs:GetQueryResults`. It never mutates infrastructure.
- **Cost control:** call the LLM only for CRITICAL / threshold-breaching incidents; cache-first + dedup;
  compact prompts; retrieval capped at top-K. Set an AWS budget alert before continuous runs.
  The multi-agent graph adds calls, so keep triage / retrievers / action / synthesize on Haiku
  (`FAST_MODEL_ID`) and reserve the main model for diagnosis + critic; cap the critic loop at
  `MAX_ROUNDS`; and rely on the cache to short-circuit the entire graph on repeats.
- **Recommend, never execute:** IIM proposes actions to a human only.
- **Clean collector abstraction:** context gathering sits behind a shared interface so a second cloud is
  "just write a new collector" later.

## 17. Existing assets (do not recreate or rewrite)

- `backend/ai/analyze_incident.py` — `SYSTEM_PROMPT`, `build_user_message()` (compact, only-present-fields
  assembly — handles both infra and non-infra incidents), `fingerprint()` (service + normalized error
  signature + deploy version), and `analyze()` (cache-first, calls Bedrock, parses JSON). Wrap
  `analyze()` behind the API using LangChain; the in-memory cache becomes Postgres. Do not write a new
  prompt or analysis logic.
- `backend/ai/samples/infra_oom.json`, `backend/ai/samples/apicost_overage.json` — anonymized test contexts.
- `README.md`, `.gitignore` — already exist.

---

## 18. Build plan (milestones within the sprint)

1. **M1 — Backend skeleton + DB.** FastAPI app, Postgres+pgvector via compose, migrations, healthz.
2. **M2 — Analysis service (single-call baseline).** Wrap `analyze_incident.py` behind
   `POST /api/incidents` using LangChain `ChatBedrockConverse`; Postgres-backed cache + fingerprint.
   This is the fallback the M3 agent graph builds on / replaces.
3. **M3 — RAG + multi-agent graph.** Document upload, chunk/embed (Titan), pgvector retrieval; then the
   LangGraph agent graph (triage + parallel retrievers + diagnosis + critic loop + action + synthesize)
   with model tiering, replacing the M2 single-call baseline.
4. **M4 — Frontend board.** React (Vite) + shadcn/ui board, incident detail, manual ingestion page.
5. **M5 — SSE.** Streaming analysis + live board feed.
6. **M6 — Auth (SSO/OAuth).**
7. **M7 — Knowledge library UI + auto-postmortem write-back.**
8. **Stretch — Azure DevOps ticketing; AWS auto-collector path.**

---

## 19. Open questions

1. **Identity provider:** Google or Microsoft (Entra) for the demo SSO? Restrict to `@emesoft.net`?
2. **RAG seed corpus:** who provides the initial anonymized runbooks/postmortems/arch docs, and in what
   format (Markdown/PDF)?
3. **Demo service(s):** keep the single-service focus (`GCM`) or show multiple?
4. **Titan availability:** confirm `amazon.titan-embed-text-v2:0` is enabled in `ap-southeast-1` (may
   need an inference-profile prefix like the chat model). Fallback embedding model if not?
5. **Collector for the AWS path:** reuse/port the planned Lambda collector, or a standalone container
   posting to `/api/incidents`?
6. **Postmortem write-back:** automatic on resolve, or human-reviewed before entering the RAG corpus?
7. **Cache TTL:** what value for `CACHE_TTL_SECONDS` in this product context?
8. **Agent budget:** is the Haiku/main-model tiering acceptable for the per-incident cost target, and
   what `MAX_ROUNDS` for the critic corrective-retrieval loop (default 2)?
9. **Baseline vs graph:** ship the M2 single-call analyzer as a fallback (feature-flagged) or go
   straight to the multi-agent graph for the demo?
