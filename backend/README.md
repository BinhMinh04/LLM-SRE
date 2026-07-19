# IIM backend

FastAPI + LangChain backend for IIM (Intelligent Incident Management). Wraps the Step 0 analysis
brain (`ai/analyze_incident.py`) behind an API, adds RAG over pgvector, and streams analysis over SSE.

See the project root `CLAUDE.md` and `.claude/specs/SPEC.md` for the full design.

## Development

```bash
uv sync                                   # install from the frozen lockfile
uv run uvicorn app.main:app --reload      # run the API on :8000
```

Or run the whole stack (Postgres + pgvector + backend) with Docker Compose:

```bash
docker compose -f ../infra/docker-compose.yml up
```

Health check: `GET /healthz`.
