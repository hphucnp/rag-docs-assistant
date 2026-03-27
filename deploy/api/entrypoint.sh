#!/usr/bin/env sh
set -eu

DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-rag_db}"
DB_USER="${POSTGRES_USER:-rag_user}"
MAX_TRIES="${DB_READY_MAX_TRIES:-60}"
SLEEP_SECONDS="${DB_READY_SLEEP_SECONDS:-2}"

echo "[entrypoint] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."

attempt=1
while [ "$attempt" -le "$MAX_TRIES" ]; do
  if DB_HOST="$DB_HOST" DB_PORT="$DB_PORT" DB_NAME="$DB_NAME" DB_USER="$DB_USER" uv run python -c '
import asyncio
import os

import asyncpg


async def main() -> None:
    conn = await asyncpg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.getenv("POSTGRES_PASSWORD", ""),
        database=os.environ["DB_NAME"],
    )
    await conn.close()


asyncio.run(main())
' >/dev/null 2>&1; then
    echo "[entrypoint] PostgreSQL is ready."
    break
  fi

  echo "[entrypoint] PostgreSQL not ready yet (attempt ${attempt}/${MAX_TRIES})."
  attempt=$((attempt + 1))
  sleep "$SLEEP_SECONDS"
done

if [ "$attempt" -gt "$MAX_TRIES" ]; then
  echo "[entrypoint] PostgreSQL did not become ready in time."
  exit 1
fi

echo "[entrypoint] Running Alembic migrations..."
uv run alembic upgrade head

echo "[entrypoint] Starting Uvicorn..."

if [ "${UVICORN_RELOAD:-false}" = "true" ] || [ "${UVICORN_RELOAD:-0}" = "1" ]; then
  exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
fi

exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"