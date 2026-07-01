"""API router aggregation."""

from fastapi import APIRouter

from app.api.contracts import router as contracts_router
from app.api.health import router as health_router
from app.api.search import router as search_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(contracts_router)
api_router.include_router(search_router)
