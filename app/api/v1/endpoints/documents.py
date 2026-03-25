import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.document import (
    AskRequest,
    AskResponse,
    DocumentIngest,
    DocumentRead,
    DownloadURLResponse,
    SearchRequest,
    SearchResult,
)
from app.services import rag, storage
from app.services.ai.exceptions import (
    ChatConfigurationError,
    ChatRateLimitError,
    ChatServiceError,
)
from app.services.document_ingestion import ingest_uploaded_file, parse_metadata

logger = logging.getLogger(__name__)
settings = get_settings()


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
        doc_type=payload.doc_type,
        use_chunking=payload.use_chunking,
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
    doc_type: Annotated[str, Form(description="'cv' or 'jd' for section-aware chunking")] = "cv",
    use_chunking: Annotated[bool, Form(description="Whether to chunk the document")] = True,
    db: AsyncSession = Depends(get_db),
):
    """Upload a .pdf, .txt, or .md file to MinIO, extract its text, embed, and store."""
    meta_dict = parse_metadata(metadata)
    return await ingest_uploaded_file(
        db,
        file,
        title=title,
        doc_type=doc_type,
        source_url=source_url,
        metadata=meta_dict,
        use_chunking=use_chunking,
    )


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
            detail="No file stored for thi2s document",
        )
    url = await storage.presigned_download_url(doc.storage_key, expires_seconds=expires)
    return DownloadURLResponse(url=url, expires_in=expires)
