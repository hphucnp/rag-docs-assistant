import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# ---------------------------------------------------------------------------
# In-memory SQLite is not supported by pgvector; tests use mocking instead.
# ---------------------------------------------------------------------------

FAKE_EMBEDDING = [0.0] * 1536
FAKE_DOC_ID = uuid.uuid4()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ingest_document(client):
    mock_doc = AsyncMock()
    mock_doc.id = FAKE_DOC_ID
    mock_doc.title = "Test Doc"
    mock_doc.content = "Some content"
    mock_doc.source_url = None
    mock_doc.storage_key = None
    mock_doc.metadata_ = {}
    mock_doc.created_at = "2026-01-01T00:00:00Z"
    mock_doc.updated_at = None

    with (
        patch("app.services.rag.embed_text", return_value=FAKE_EMBEDDING),
        patch("app.api.v1.endpoints.documents.rag.ingest_document", return_value=mock_doc),
    ):
        resp = await client.post(
            "/api/v1/documents/ingest",
            json={"title": "Test Doc", "content": "Some content"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Doc"


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search(client):
    from app.schemas.document import SearchResult

    fake_results = [
        SearchResult(
            id=FAKE_DOC_ID,
            title="Test Doc",
            content="Some content",
            source_url=None,
            score=0.95,
        )
    ]

    with patch(
        "app.api.v1.endpoints.documents.rag.similarity_search",
        return_value=fake_results,
    ):
        resp = await client.post(
            "/api/v1/documents/search",
            json={"query": "test query", "top_k": 3},
        )

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["score"] == 0.95


# ---------------------------------------------------------------------------
# Ask
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ask(client):
    from app.schemas.document import SearchResult

    fake_sources = [
        SearchResult(
            id=FAKE_DOC_ID,
            title="Test Doc",
            content="Some content",
            source_url=None,
            score=0.9,
        )
    ]

    with patch(
        "app.api.v1.endpoints.documents.rag.ask",
        return_value=("Based on the context, pgvector stores embeddings.", fake_sources),
    ):
        resp = await client.post(
            "/api/v1/documents/ask",
            json={"question": "What is pgvector?", "top_k": 3},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert len(body["sources"]) == 1


# ---------------------------------------------------------------------------
# 404 cases
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_document_not_found(client):
    with patch("app.api.v1.endpoints.documents.rag.get_document", return_value=None):
        resp = await client.get(f"/api/v1/documents/{FAKE_DOC_ID}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_document_not_found(client):
    with patch("app.api.v1.endpoints.documents.rag.delete_document", return_value=False):
        resp = await client.delete(f"/api/v1/documents/{FAKE_DOC_ID}")
    assert resp.status_code == 404
