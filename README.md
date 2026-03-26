# rag-docs-assistant

A **Retrieval-Augmented Generation (RAG)** API built with **FastAPI**, **PostgreSQL**, and **pgvector**.  
Ingest documents, store their embeddings, perform semantic search, and ask natural-language questions grounded in your own knowledge base.

---

## Tech Stack

| Layer            | Technology                   |
| ---------------- | ---------------------------- |
| API              | FastAPI + Uvicorn            |
| Vector DB        | PostgreSQL 16 + pgvector     |
| ORM / Migrations | SQLAlchemy (async) + Alembic |
| Embeddings       | Ollama / OpenAI / Cohere     |
| LLM              | Groq / OpenAI                |
| Containers       | Docker + Docker Compose      |

---

## Project Structure

```
rag-docs-assistant/
├── app/
│   ├── main.py              # FastAPI app & middleware
│   ├── config.py            # Pydantic-settings configuration
│   ├── database.py          # Async SQLAlchemy engine & session
│   ├── models/
│   │   └── document.py      # Document ORM model (with pgvector column)
│   ├── schemas/
│   │   └── document.py      # Pydantic request/response schemas
│   ├── services/
│   │   ├── ai/              # Provider interfaces + concrete providers
│   │   ├── embedding.py     # Embedding facade with retry
│   │   └── rag.py           # Ingest, search, ask, CRUD logic
│   └── api/v1/
│       ├── router.py
│       └── endpoints/
│           └── documents.py # REST endpoints
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial.py   # Enable pgvector + create documents table
├── tests/
│   └── test_documents.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── uv.lock
└── alembic.ini
```

---

## Quick Start

### 1. Clone & configure

```bash
cp .env.example .env
# Edit .env and add keys based on selected providers
```

Provider switching is config-only:

```bash
# Option A: default (local + cheap)
EMBEDDING_PROVIDER=ollama
CHAT_PROVIDER=groq

# Option B: OpenAI for both
EMBEDDING_PROVIDER=openai
CHAT_PROVIDER=openai

# Option C: Cohere embeddings + Groq chat
EMBEDDING_PROVIDER=cohere
CHAT_PROVIDER=groq
```

### 2. Start services

```bash
docker compose up --build
```

For detached mode (recommended on servers):

```bash
docker compose up -d --build
```

Pull the embedding model in Ollama:

```bash
docker compose exec ollama ollama pull nomic-embed-text
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`
Demo UI: `http://localhost:8000/demo`

If Caddy is enabled (default in `docker-compose.yml`), use your domain over HTTPS:

- API: `https://<your-domain>`
- Docs: `https://<your-domain>/docs`
- Demo UI: `https://<your-domain>/demo`

### 3. Run migrations

```bash
docker compose exec api alembic upgrade head
```

### 4. Configure HTTPS (Caddy)

Before running on a public server, set these values in `.env`:

```bash
APP_DOMAIN=rag.example.com
ACME_EMAIL=you@example.com
```

Requirements:

- DNS `A` record of `APP_DOMAIN` points to your server IP
- Ports `80` and `443` are open in firewall/security group

Caddy will automatically provision and renew TLS certificates from Let's Encrypt.

### 5. Use Squid proxy (optional)

Squid listens on `3128` and is restricted to private networks by default.
If you need external access, update `deploy/squid/squid.conf` ACL rules before exposing port `3128` publicly.

---

## API Endpoints

| Method   | Path                                   | Description                             |
| -------- | -------------------------------------- | --------------------------------------- |
| `GET`    | `/health`                              | Health check                            |
| `POST`   | `/api/v1/documents/ingest`             | Ingest a document (generates embedding) |
| `GET`    | `/api/v1/documents/`                   | List all documents                      |
| `GET`    | `/api/v1/documents/{id}`               | Get a document by ID                    |
| `DELETE` | `/api/v1/documents/{id}`               | Delete a document                       |
| `POST`   | `/api/v1/documents/search`             | Semantic similarity search              |
| `POST`   | `/api/v1/documents/ask`                | RAG: retrieve context + LLM answer      |
| `POST`   | `/api/v1/documents/upload`             | Upload file to MinIO and ingest content |
| `POST`   | `/api/v1/match/upload-bundle`          | Upload CV + JD + optional notes         |
| `POST`   | `/api/v1/match/missing-skills`         | Compare CV vs JD for skill gaps         |
| `POST`   | `/api/v1/match/rewrite-summary`        | Rewrite summary for target job          |
| `POST`   | `/api/v1/match/highlight-achievements` | Pick the best achievements              |

## Demo UI

Open `http://localhost:8000/demo` to run the end-to-end CV/JD matching demo.

Flow:

1. Upload a CV file and a JD file
2. Optionally add notes such as recruiter context or what to emphasize
3. Click the three actions to generate:

- missing skills
- rewritten summary
- achievements to highlight

The demo page calls these APIs under the hood:

```bash
POST /api/v1/match/upload-bundle
POST /api/v1/match/missing-skills?cv_id=...&jd_id=...&notes_id=...
POST /api/v1/match/rewrite-summary?cv_id=...&jd_id=...&notes_id=...
POST /api/v1/match/highlight-achievements?cv_id=...&jd_id=...&notes_id=...
```

## Vue Frontend

A Vue + Vite + Tailwind frontend is available in [`frontend/`](./frontend) and mirrors the existing demo workflow with a dedicated dev server.

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

By default, Vite proxies `/api` requests to `http://localhost:8000`, so you can run the FastAPI backend and the Vue app side by side during development.

For Docker Compose development, use the `frontend` service. It runs the Vite dev server on `http://localhost:5173` and proxies API traffic to the `api` container:

```bash
docker compose up frontend api
```

If Caddy is running too, `http://localhost:80` serves the frontend and forwards `/api/*`, `/docs`, `/redoc`, and `/health` to the backend. `http://localhost:8000` remains backend-only. Local Docker Compose no longer binds `:443`; keep HTTPS/TLS only for production deployment.

If your API is on another host, create `frontend/.env.local`:

```bash
VITE_API_BASE_URL=https://your-api-host
VITE_DEV_PROXY_TARGET=http://localhost:8000
```

To build the frontend assets separately:

```bash
cd frontend
npm run build
```

This writes the production bundle to `app/static/demo_app/`. The Docker image still includes that bundle, but in local Compose development the frontend is served through the dedicated `frontend` service and Caddy on port `80`.

### Example: Ingest

```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{"title": "pgvector Intro", "content": "pgvector is a PostgreSQL extension for storing and querying vector embeddings."}'
```

### Example: Ask

```bash
curl -X POST http://localhost:8000/api/v1/documents/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is pgvector?", "top_k": 3}'
```

---

## Local Development (without Docker)

Python requirement: 3.13+

```bash
uv sync --group dev

# Start Postgres separately, then:
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Running Tests

```bash
uv run pytest
```

## Package Management (uv)

```bash
# Add a runtime dependency
uv add <package>

# Add a development dependency
uv add --dev <package>

# Remove a dependency
uv remove <package>

# Regenerate lockfile after dependency changes
uv lock
```

## Linting (Ruff)

```bash
uv run ruff check .
uv run ruff format .
```
