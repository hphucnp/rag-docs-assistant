import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.config import get_settings
from app.services.storage import ensure_bucket

settings = get_settings()

logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_bucket()
    yield


_app = FastAPI(
    title="RAG Docs Assistant",
    description="Retrieval-Augmented Generation API backed by PostgreSQL + pgvector",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

cors_allowed_origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
if not cors_allowed_origins:
    cors_allowed_origins = ["*"]

_app.include_router(api_v1_router, prefix="/api/v1")


@_app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


@_app.get("/", tags=["Health"])
async def api_root():
    return {
        "service": "rag-docs-assistant-api",
        "status": "ok",
        "docs": "/docs",
    }


# Wrap the whole ASGI app so CORS headers are also present on error responses.
app = CORSMiddleware(
    app=_app,
    allow_origins=cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
