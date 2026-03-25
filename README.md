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
| Embeddings       | Ollama `nomic-embed-text`    |
| LLM              | Groq (OpenAI-compatible API) |
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
├── requirements.txt
├── pyproject.toml
└── alembic.ini
```

---

## Quick Start

### 1. Clone & configure

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Start services

```bash
docker compose up --build
```

Pull the embedding model in Ollama:

```bash
docker compose exec ollama ollama pull nomic-embed-text
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### 3. Run migrations

```bash
docker compose exec api alembic upgrade head
```

---

## API Endpoints

| Method   | Path                       | Description                             |
| -------- | -------------------------- | --------------------------------------- |
| `GET`    | `/health`                  | Health check                            |
| `POST`   | `/api/v1/documents/ingest` | Ingest a document (generates embedding) |
| `GET`    | `/api/v1/documents/`       | List all documents                      |
| `GET`    | `/api/v1/documents/{id}`   | Get a document by ID                    |
| `DELETE` | `/api/v1/documents/{id}`   | Delete a document                       |
| `POST`   | `/api/v1/documents/search` | Semantic similarity search              |
| `POST`   | `/api/v1/documents/ask`    | RAG: retrieve context + LLM answer      |
| `POST`   | `/api/v1/documents/upload` | Upload file to MinIO and ingest content |

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

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start Postgres separately, then:
alembic upgrade head
uvicorn app.main:app --reload
```

## Running Tests

```bash
pytest
```
