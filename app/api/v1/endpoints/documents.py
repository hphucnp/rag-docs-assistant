import io
import json
import uuid
from typing import Annotated

import pypdf
from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, status
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
from app.services import rag, storage

_TEXT_TYPES = {"text/plain", "text/markdown", "text/x-markdown"}
_PDF_TYPES = {"application/pdf"}
_ALLOWED_TYPES = _TEXT_TYPES | _PDF_TYPES


def _extract_text(data: bytes, content_type: str, filename: str) -> str:
    ct = content_type.split(";")[0].strip().lower()
    if ct in _PDF_TYPES or filename.lower().endswith(".pdf"):
        reader = pypdf.PdfReader(io.BytesIO(data))
        pages = [p.extract_text() for p in reader.pages if p.extract_text()]
        if not pages:
            raise HTTPException(status_code=422, detail="Could not extract text from PDF")
        return "\n\n".join(pages)
    return data.decode("utf-8", errors="replace")

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


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Storage"],
    summary="Upload a file, store in MinIO, and ingest",
)
async def upload_document(
    file: UploadFile,
    title: Annotated[str, Form(max_length=512)],
    source_url: Annotated[str | None, Form()] = None,
    metadata: Annotated[str | None, Form(description="JSON object string")] = None,
    db: AsyncSession = Depends(get_db),
):
    """Upload a .pdf, .txt, or .md file to MinIO, extract its text, embed, and store."""
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"
    ct_base = content_type.split(";")[0].strip().lower()

    if ct_base not in _ALLOWED_TYPES and not filename.lower().endswith((".pdf", ".txt", ".md")):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {content_type}. Allowed: pdf, txt, md",
        )

    data = await file.read()

    try:
        meta_dict: dict = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="'metadata' must be a valid JSON object")

    object_key = await storage.upload_file(data, filename, content_type)

    try:
        text = _extract_text(data, content_type, filename)
    except HTTPException:
        await storage.delete_file(object_key)
        raise

    doc = await rag.ingest_document(
        db,
        title=title,
        content=text,
        source_url=source_url,
        storage_key=object_key,
        metadata=meta_dict,
    )
    return doc


@router.get(
    "/{document_id}/download-url",
    tags=["Storage"],
    summary="Get a pre-signed download URL for the original file",
)
async def download_url(
    document_id: uuid.UUID,
    expires: int = Query(3600, ge=60, le=86400, description="URL validity in seconds"),
    db: AsyncSession = Depends(get_db),
):
    doc = await rag.get_document(db, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if not doc.storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No file stored for this document",
        )
    url = await storage.presigned_download_url(doc.storage_key, expires_seconds=expires)
    return {"url": url, "expires_in": expires}
