import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.document import (
    AskRequest,
    AskResponse,
    DocumentIngest,
    DocumentRead,
    SearchRequest,
    SearchResult,
)
from app.services import rag

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/ingest",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a document",
)
async def ingest(payload: DocumentIngest, db: AsyncSession = Depends(get_db)):
    """Embed and store a document in the vector store."""
    doc = await rag.ingest_document(
        db,
        title=payload.title,
        content=payload.content,
        source_url=payload.source_url,
        metadata=payload.metadata,
    )
    return doc


@router.get(
    "/",
    response_model=list[DocumentRead],
    summary="List documents",
)
async def list_documents(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await rag.list_documents(db, offset=offset, limit=limit)


@router.get(
    "/{document_id}",
    response_model=DocumentRead,
    summary="Get a document by ID",
)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    doc = await rag.get_document(db, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    deleted = await rag.delete_document(db, document_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


@router.post(
    "/search",
    response_model=list[SearchResult],
    summary="Semantic similarity search",
)
async def search(payload: SearchRequest, db: AsyncSession = Depends(get_db)):
    """Find the top-k documents most semantically similar to the query."""
    return await rag.similarity_search(db, query=payload.query, top_k=payload.top_k)


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question (RAG)",
)
async def ask(payload: AskRequest, db: AsyncSession = Depends(get_db)):
    """Retrieve relevant documents and generate a grounded answer."""
    answer, sources = await rag.ask(db, question=payload.question, top_k=payload.top_k)
    return AskResponse(answer=answer, sources=sources)
