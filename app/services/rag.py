import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.document import Chunk, Document
from app.schemas.document import SearchResult
from app.services.ai.factory import get_chat_service
from app.services.chunking import chunk_by_sections
from app.services.embedding import embed_batch, embed_text

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
    doc_type: str = "cv",
    use_chunking: bool = True,
) -> Document:
    """
    Ingest a document: optionally chunk it, generate embeddings, and store.

    Args:
        db: Database session
        title: Document title
        content: Document content
        source_url: Optional source URL
        storage_key: Optional storage reference (e.g., MinIO key)
        metadata: Optional metadata dict
        doc_type: "cv" or "jd" for section-aware chunking
        use_chunking: Whether to chunk the document
    """
    # Create document record
    doc = Document(
        title=title,
        content=content,
        source_url=source_url,
        storage_key=storage_key,
        metadata_=metadata or {},
    )
    db.add(doc)
    await db.flush()  # Flush to get doc.id before adding chunks

    if use_chunking:
        # Chunk the document
        chunks_data = chunk_by_sections(content, doc_type=doc_type, chunk_size=400)

        # Extract texts and embed as batch
        chunk_texts = [c.text for c in chunks_data]
        embeddings = await embed_batch(chunk_texts)

        # Create Chunk records
        for chunk_data, embedding in zip(chunks_data, embeddings):
            chunk = Chunk(
                document_id=doc.id,
                content=chunk_data.text,
                section=chunk_data.section,
                start_idx=chunk_data.start_idx,
                end_idx=chunk_data.end_idx,
                embedding=embedding,
                metadata_={"doc_type": doc_type},
            )
            db.add(chunk)

        logger.info("Chunked document id=%s into %d chunks", doc.id, len(chunks_data))
    else:
        # No chunking: embed full content as single chunk
        embedding = await embed_text(content)
        chunk = Chunk(
            document_id=doc.id,
            content=content,
            section=None,
            start_idx=0,
            end_idx=len(content),
            embedding=embedding,
            metadata_={"doc_type": doc_type},
        )
        db.add(chunk)

    await db.commit()
    await db.refresh(doc)
    logger.info("Ingested document id=%s title=%r with %d chunks", doc.id, doc.title, len(doc.chunks))
    return doc


async def similarity_search(
    db: AsyncSession,
    *,
    query: str,
    top_k: int = 5,
    document_ids: list[uuid.UUID] | None = None,
) -> list[SearchResult]:
    """Return the top-k chunks most similar to the query."""
    query_embedding = await embed_text(query)

    # Search chunks instead of documents
    stmt = (
        select(
            Chunk,
            Document,
            (1 - Chunk.embedding.cosine_distance(query_embedding)).label("score"),
        )
        .join(Document, Chunk.document_id == Document.id)
        .where(Chunk.embedding.is_not(None))
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    if document_ids:
        stmt = stmt.where(Document.id.in_(document_ids))

    result = await db.execute(stmt)
    rows = result.all()

    return [
        SearchResult(
            id=doc.id,
            title=doc.title,
            content=chunk.content,  # Use chunk content, not full doc content
            source_url=doc.source_url,
            score=round(float(score), 4),
        )
        for chunk, doc, score in rows
    ]


async def ask(
    db: AsyncSession,
    *,
    question: str,
    top_k: int = 5,
) -> tuple[str, list[SearchResult]]:
    """RAG pipeline: retrieve relevant chunks, then generate an LLM answer."""
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

    chat_service = get_chat_service()
    answer = await chat_service.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=settings.llm_model,
        temperature=0.2,
    )
    return answer, sources


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one_or_none()


async def list_documents(db: AsyncSession, *, offset: int = 0, limit: int = 20) -> list[Document]:
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
