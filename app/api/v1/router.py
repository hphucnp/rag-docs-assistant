from fastapi import APIRouter

from app.api.v1.endpoints.documents import router as documents_router
from app.api.v1.endpoints.match import router as match_router
from app.api.v1.endpoints.webhook import router as webhook_router

router = APIRouter()
router.include_router(documents_router)
router.include_router(match_router)
router.include_router(webhook_router)
