"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.redis import close_redis
from app.middleware.request_id import RequestIDMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("ClauseGuard API starting up (env=%s)", settings.app_env)

    # Create MinIO bucket on startup
    try:
        from app.core.storage import ensure_bucket_exists

        ensure_bucket_exists()
        logger.info("MinIO bucket check complete")
    except Exception as e:
        logger.warning("MinIO bucket check failed: %s", e)

    yield

    # Shutdown
    await close_redis()
    logger.info("ClauseGuard API shut down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ClauseGuard API",
        description="AI-Powered Contract Review Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware (order matters -- outermost first)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(api_router)

    return app


app = create_app()
