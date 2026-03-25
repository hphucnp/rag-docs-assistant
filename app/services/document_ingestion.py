import io
import json
import logging
from typing import Any

import pypdf
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import RetryError

from app.config import get_settings
from app.models.document import Document
from app.services import rag, storage
from app.services.ai.exceptions import EmbeddingRateLimitError, EmbeddingServiceError

logger = logging.getLogger(__name__)
settings = get_settings()

_TEXT_TYPES = {"text/plain", "text/markdown", "text/x-markdown"}
_PDF_TYPES = {"application/pdf"}
_ALLOWED_TYPES = _TEXT_TYPES | _PDF_TYPES
_ALLOWED_EXTENSIONS = (".pdf", ".txt", ".md")


def parse_metadata(metadata: str | None) -> dict[str, Any]:
    if metadata is None or metadata.strip() == "":
        return {}
    try:
        value = json.loads(metadata)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="metadata must be valid JSON") from exc

    if not isinstance(value, dict):
        raise HTTPException(status_code=422, detail="metadata must be a JSON object")
    return value


def validate_upload_payload(filename: str, content_type: str, size: int) -> None:
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


def extract_text(data: bytes, content_type: str, filename: str) -> str:
    ct = content_type.split(";")[0].strip().lower()
    if ct in _PDF_TYPES or filename.lower().endswith(".pdf"):
        reader = pypdf.PdfReader(io.BytesIO(data))
        pages = [page.extract_text() for page in reader.pages if page.extract_text()]
        if not pages:
            raise HTTPException(status_code=422, detail="Could not extract text from PDF")
        return "\n\n".join(pages)
    return data.decode("utf-8", errors="replace")


async def ingest_uploaded_file(
    db: AsyncSession,
    file: UploadFile,
    *,
    title: str,
    doc_type: str,
    source_url: str | None = None,
    metadata: dict[str, Any] | None = None,
    use_chunking: bool = True,
) -> Document:
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=422, detail="filename is required")

    content_type = file.content_type or "application/octet-stream"
    data = await file.read()
    validate_upload_payload(filename, content_type, len(data))

    object_key = await storage.upload_file(data, filename, content_type)
    try:
        text = extract_text(data, content_type, filename)
    except HTTPException:
        await storage.delete_file(object_key)
        raise

    try:
        document = await rag.ingest_document(
            db,
            title=title,
            content=text,
            source_url=source_url,
            storage_key=object_key,
            metadata=metadata,
            doc_type=doc_type,
            use_chunking=use_chunking,
        )
        return document
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
