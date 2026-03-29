# rag-docs-assistant

A **Retrieval-Augmented Generation (RAG)** API built with **FastAPI**, **PostgreSQL**, and **pgvector**.  
Ingest documents, store their embeddings, perform semantic search, and ask natural-language questions grounded in your own knowledge base.

It also includes a focused CV / Job Description matching workflow with a Vue frontend for:

- uploading a CV, a job description, and optional notes
- identifying missing or weak skills
- rewriting the candidate summary for the target role
- surfacing the achievements most worth highlighting

## Highlights

- Async FastAPI backend with provider-based AI integration
- PostgreSQL + pgvector for semantic retrieval
- CV / JD matching workflow with a clean Vue frontend
- Local-first embedding option via Ollama
- Production deployment path with Docker Compose and Caddy

## Table of Contents

- [What This Project Does](#what-this-project-does)
- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Providers](#providers)
- [API Endpoints](#api-endpoints)
- [Typical Workflows](#typical-workflows)
- [Vue Frontend](#vue-frontend)
- [Local Development](#local-development-without-docker)
- [Running Tests](#running-tests)
- [Security Notes](#security-notes)

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

## What This Project Does

This repo combines three layers:

1. A FastAPI backend for document ingestion, chunking, embedding, retrieval, and generation
2. A PostgreSQL + pgvector store for semantic search over uploaded content
3. A Vue frontend for the CV / JD matching flow and demo experience

At a high level, the request flow looks like this:

```text
Upload document(s) -> extract text -> chunk content -> generate embeddings
-> store vectors in PostgreSQL/pgvector -> retrieve relevant chunks
-> send prompt + retrieved context to selected LLM provider -> return answer
```

For the CV / JD workflow, the system stores the CV, job description, and optional notes as separate documents, retrieves the most relevant chunks for each action, and then asks the configured LLM to generate the final output.

## Why It Exists

Many RAG examples stop at a generic "upload and ask" demo. This project pushes a step further by packaging retrieval, generation, and a task-specific UI into a workflow that is easier to evaluate in a real product context.

The CV / JD flow is the clearest example: the app does not just retrieve text, it helps turn that retrieval into outputs that are directly useful in a hiring workflow.

## Features

- Document ingestion from raw text or uploaded files
- Semantic similarity search with pgvector
- RAG question answering grounded in retrieved document chunks
- Provider-based embeddings with `ollama`, `openai`, or `cohere`
- Provider-based chat generation with `groq` or `openai`
- CV / JD matching endpoints for missing skills, summary rewriting, and achievement highlighting
- Vue frontend for local development and demo use
- Docker Compose setup for development and production
- HTTPS-ready reverse proxy setup with Caddy

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

### Prerequisites

- Docker and Docker Compose for the containerized workflow
- Python `3.13+` if running the backend locally without Docker
- Node.js if running the Vue frontend outside Docker
- Provider credentials for whichever external services you enable

### Configuration Overview

The app separates:

- `EMBEDDING_PROVIDER`: where embeddings come from
- `CHAT_PROVIDER`: where text generation comes from
- `EMBEDDING_MODEL`: embedding model name
- `LLM_MODEL`: chat model name passed to the selected chat provider

Example:

```bash
CHAT_PROVIDER=groq
LLM_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```

This means the app sends chat requests to Groq and asks Groq to run that Llama-family model.

### 1. Clone & configure

```bash
cp .env.example .env
# Edit .env and add keys based on selected providers
# Do not commit your populated .env file or any real secrets
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

Minimal variables to review before first run:

- `CHAT_PROVIDER`
- `EMBEDDING_PROVIDER`
- `LLM_MODEL`
- `EMBEDDING_MODEL`
- provider API keys for any hosted services you enable
- `CORS_ALLOWED_ORIGINS` for browser-based access
- `FRONTEND_DOMAIN`, `API_DOMAIN`, and `ACME_EMAIL` for production HTTPS

### 2. Start services

```bash
docker compose up --build
```

For detached mode (recommended on servers):

```bash
docker compose up -d --build
```

This starts:

- `db`: PostgreSQL with pgvector
- `minio`: object storage for uploaded files
- `ollama`: local embedding model host
- `api`: FastAPI backend
- `frontend`: Vite dev server in local Compose
- `caddy`: local reverse proxy
- `squid`: optional proxy service

Pull the embedding model in Ollama:

```bash
docker compose exec ollama ollama pull nomic-embed-text
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`
Frontend via Caddy: `http://localhost`

For production on a public server, use the production compose file:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

With the domain setup below, public endpoints become:

- Frontend: `https://rag.example.com`
- API: `https://api.example.com`
- Docs: `https://api.example.com/docs`

### 3. Run migrations

```bash
docker compose exec api alembic upgrade head
```

If this is a fresh environment, wait for PostgreSQL to become healthy before running migrations.

### 4. Configure HTTPS (Caddy)

Before running production on DigitalOcean, set these values in `.env`:

```bash
FRONTEND_DOMAIN=rag.example.com
API_DOMAIN=api.example.com
ACME_EMAIL=ops@example.com
```

Requirements:

- DNS `A` record of `rag.example.com` points to your server IP
- DNS `A` record of `api.example.com` points to your server IP
- Ports `80` and `443` are open in firewall/security group

The production override uses [`deploy/caddy/Caddyfile.production`](./deploy/caddy/Caddyfile.production). Caddy will automatically provision and renew TLS certificates from Let's Encrypt.

### 5. Use Squid proxy (optional)

Squid listens on `3128` and is restricted to private networks by default.
If you need external access, update `deploy/squid/squid.conf` ACL rules before exposing port `3128` publicly.

---

## Providers

### Embedding providers

| Provider | Purpose | Notes |
| -------- | ------- | ----- |
| `ollama` | local embeddings | default local-first option |
| `openai` | hosted embeddings | requires `OPENAI_API_KEY` |
| `cohere` | hosted embeddings | requires `COHERE_API_KEY` |

### Chat providers

| Provider | Purpose | Notes |
| -------- | ------- | ----- |
| `groq` | hosted chat inference | model name comes from `LLM_MODEL` |
| `openai` | hosted chat inference | model name comes from `LLM_MODEL` |

The code currently supports self-hosted Ollama for embeddings, but not yet as a chat provider. If you want self-hosted Llama generation inside this repo, you would need to add an Ollama chat provider or another self-hosted inference adapter.

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

Open `http://localhost` to run the end-to-end CV/JD matching demo locally.

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

## Typical Workflows

### Generic RAG API

1. Ingest one or more documents
2. Search semantically or ask a question
3. Use retrieved chunks as grounded context for the final answer

### CV / JD match workflow

1. Upload a CV file and a job description file
2. Optionally attach recruiter or application notes
3. Use the returned document IDs to run the three match actions
4. Review the generated missing skills, rewritten summary, and highlighted achievements

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

For production on DigitalOcean with HTTPS, use the production override and [`deploy/caddy/Caddyfile.production`](./deploy/caddy/Caddyfile.production). For your domain layout:

- frontend: `rag.example.com`
- backend: `api.example.com`

Set these values in `.env` on the server:

```bash
FRONTEND_DOMAIN=rag.example.com
API_DOMAIN=api.example.com
ACME_EMAIL=ops@example.com
```

Required DNS records in DigitalOcean:

- `A rag.example.com -> <your-droplet-ip>`
- `A api.example.com -> <your-droplet-ip>`

Start production on the Droplet with:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Production Caddy publishes ports `80` and `443`, routes `rag.example.com` to the frontend container, and routes `api.example.com` to the FastAPI container.

If your API is on another host in local dev, create `frontend/.env.local`:

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

In production, Caddy serves the built static frontend directly.

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

## Security Notes

- Never commit a populated `.env` file
- Use neutral placeholders in documentation and examples
- Keep API keys and webhook secrets in server-side environment variables
- Review Caddy, Squid, and MinIO exposure before opening services to the public

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
