# IIM backend image. Built from the official uv image; installs from the frozen lockfile.
# uv Docker guide: https://docs.astral.sh/uv/guides/integration/docker/
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install deps first (cached layer) from the lockfile, without the project itself.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Then the source.
COPY . .

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

# Apply migrations, then serve. DATABASE_URL is provided by compose / env.
CMD ["sh", "-c", "uv run --no-dev alembic upgrade head && uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port 8000"]
