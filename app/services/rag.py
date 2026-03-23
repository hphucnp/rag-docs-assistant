import logging
import uuid
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.document import Document
from app.schemas.document import SearchResult
from app.services.embedding import embed_text, get_openai_client

logger = logging.getLogger(__name__)
settings = get_settings()


async def ingest_document(
    db: AsyncSession,
    *,
    title: str,
    content: str,
    source_url: str | None = None,
    storage_key: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Document:
    """Ingest a document: generate its embedding and store it."""
    embedding = await embed_text(content)

    doc = Document(
        title=title,
        content=content,
        source_url=source_url,
        storage_key=storage_key,
        metadata_=metadata or {},
        embedding=embedding,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    logger.info("Ingested document id=%s title=%r", doc.id, doc.title)
    return doc


async def similarity_search(
    db: AsyncSession,
    *,
    query: str,
    top_k: int = 5,
) -> list[SearchResult]:
    """Return the top-k documents most similar to the query."""
    query_embedding = await embed_text(query)

    # cosine_distance returns 0 (identical) → 2 (opposite); similarity = 1 - distance/2
    stmt = (
        select(
            Document,
            (1 - Document.embedding.cosine_distance(query_embedding)).label("score"),
        )
        .where(Document.embedding.is_not(None))
        .order_by(Document.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        SearchResult(
            id=doc.id,
            title=doc.title,
            content=doc.content,
            source_url=doc.source_url,
            score=round(float(score), 4),
        )
        for doc, score in rows
    ]


async def ask(
    db: AsyncSession,
    *,
    question: str,
    top_k: int = 5,
) -> tuple[str, list[SearchResult]]:
    """RAG pipeline: retrieve relevant docs, then generate an LLM answer."""
    sources = await similarity_search(db, query=question, top_k=top_k)

    context_blocks = "\n\n---\n\n".join(
        f"[{i + 1}] {src.title}\n{src.content}" for i, src in enumerate(sources)
    )

    system_prompt = (
        "You are a helpful assistant. Use ONLY the provided context to answer the question. "
        "If the context does not contain enough information, say so. "
        "Cite the source numbers [1], [2], etc. where relevant."
    )
    user_prompt = f"Context:\n{context_blocks}\n\nQuestion: {question}"

    client: AsyncOpenAI = get_openai_client()
    completion = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    answer = completion.choices[0].message.content or ""
    return answer, sources


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one_or_none()


async def list_documents(
    db: AsyncSession, *, offset: int = 0, limit: int = 20
) -> list[Document]:
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def delete_document(db: AsyncSession, document_id: uuid.UUID) -> bool:
    doc = await get_document(db, document_id)
    if doc is None:
        return False
    storage_key = doc.storage_key
    await db.delete(doc)
    await db.commit()
    if storage_key:
        from app.services.storage import delete_file
        await delete_file(storage_key)
    return True
