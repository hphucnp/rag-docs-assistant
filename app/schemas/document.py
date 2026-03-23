import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentIngest(BaseModel):
    """Payload to ingest a new document."""

    title: str = Field(..., max_length=512, examples=["FastAPI Guide"])
    content: str = Field(..., min_length=1, examples=["FastAPI is a modern web framework..."])
    source_url: str | None = Field(None, examples=["https://fastapi.tiangolo.com"])
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: str
    source_url: str | None
    storage_key: str | None
    metadata_: dict[str, Any] = Field(alias="metadata_", serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime | None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["How does dependency injection work?"])
    top_k: int = Field(5, ge=1, le=20)


class SearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: str
    source_url: str | None
    score: float = Field(..., description="Cosine similarity score (0–1, higher is better)")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["What is pgvector used for?"])
    top_k: int = Field(5, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchResult]
