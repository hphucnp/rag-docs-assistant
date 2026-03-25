import io
import json
import logging
import uuid
from typing import Annotated, Any

import pypdf
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from tenacity import RetryError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.document import (
    AskRequest,
    AskResponse,
    DownloadURLResponse,
    DocumentIngest,
    DocumentRead,
    SearchRequest,
    SearchResult,
)
from app.services.ai.exceptions import (
    ChatConfigurationError,
    ChatRateLimitError,
    ChatServiceError,
    EmbeddingRateLimitError,
    EmbeddingServiceError,
)
from app.services import rag, storage

_TEXT_TYPES = {"text/plain", "text/markdown", "text/x-markdown"}
_PDF_TYPES = {"application/pdf"}
_ALLOWED_TYPES = _TEXT_TYPES | _PDF_TYPES
_ALLOWED_EXTENSIONS = (".pdf", ".txt", ".md")

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_metadata(metadata: str | None) -> dict[str, Any]:
    if metadata is None or metadata.strip() == "":
        return {}
    try:
        value = json.loads(metadata)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="metadata must be valid JSON") from exc

    if not isinstance(value, dict):
        raise HTTPException(status_code=422, detail="metadata must be a JSON object")
    return value


def _validate_upload_payload(filename: str, content_type: str, size: int) -> None:
    if size == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    max_size = settings.max_upload_size_mb * 1024 * 1024
    if size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB",
        )

    ct_base = content_type.split(";")[0].strip().lower()
    has_allowed_extension = filename.lower().endswith(_ALLOWED_EXTENSIONS)
    if ct_base not in _ALLOWED_TYPES and not has_allowed_extension:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {content_type}. Allowed: pdf, txt, md",
        )


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
    try:
        answer, sources = await rag.ask(db, question=payload.question, top_k=payload.top_k)
        return AskResponse(answer=answer, sources=sources)
    except ChatConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chat provider configuration error: {str(exc)}",
        ) from exc
    except ChatRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Chat provider rate limited. Please try again later.",
        ) from exc
    except ChatServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chat provider error: {str(exc)}",
        ) from exc


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Storage"],
    summary="Upload a file, store in MinIO, and ingest",
)
async def upload_document(
    file: Annotated[UploadFile, File(description="Document file (.pdf, .txt, .md)")],
    title: Annotated[str, Form(min_length=1, max_length=512)],
    source_url: Annotated[str | None, Form()] = None,
    metadata: Annotated[str | None, Form(description="JSON object string")] = None,
    db: AsyncSession = Depends(get_db),
):
    """Upload a .pdf, .txt, or .md file to MinIO, extract its text, embed, and store."""
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=422, detail="filename is required")

    content_type = file.content_type or "application/octet-stream"
    data = await file.read()
    _validate_upload_payload(filename, content_type, len(data))
    meta_dict = _parse_metadata(metadata)

    object_key = await storage.upload_file(data, filename, content_type)
    try:
        text = _extract_text(data, content_type, filename)
    except HTTPException:
        await storage.delete_file(object_key)
        raise

    try:
        doc = await rag.ingest_document(
            db,
            title=title,
            content=text,
            source_url=source_url,
            storage_key=object_key,
            metadata=meta_dict,
        )
        return doc
    except RetryError as exc:
        logger.exception("Embedding failed after max retries, deleting object %s", object_key)
        await storage.delete_file(object_key)

        inner_exc = exc.last_attempt.exception()
        if isinstance(inner_exc, EmbeddingRateLimitError):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Embedding provider rate limited. Please try again later.",
            ) from exc
        if isinstance(inner_exc, EmbeddingServiceError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Embedding provider error: {str(inner_exc)}",
            ) from exc
        raise
    except EmbeddingRateLimitError as exc:
        logger.exception("Embedding provider rate limit, deleting object %s", object_key)
        await storage.delete_file(object_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Embedding provider rate limited. Please try again later.",
        ) from exc
    except EmbeddingServiceError as exc:
        logger.exception("Embedding provider error, deleting object %s", object_key)
        await storage.delete_file(object_key)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Embedding provider error: {str(exc)}",
        ) from exc
    except Exception:
        logger.exception("Failed to ingest uploaded document, deleting object %s", object_key)
        await storage.delete_file(object_key)
        raise
    finally:
        await file.close()


@router.get(
    "/{document_id}/download-url",
    response_model=DownloadURLResponse,
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
    return DownloadURLResponse(url=url, expires_in=expires)
