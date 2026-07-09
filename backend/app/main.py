"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.router import api_router
from app.core.config import settings
from app.core.database import dispose_engine
from app.core.errors import register_exception_handlers
from app.core.redis import close_redis
from app.core.tracing import setup_tracing
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

# Install the tracer provider for the API process before the app is built, so
# FastAPI instrumentation below attaches to a configured provider. Also
# instruments Celery so the pipeline dispatch from the upload endpoint carries
# trace context into the queue.
setup_tracing("api")


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
    await dispose_engine()
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

    # Middleware. In Starlette the FIRST middleware added is the
    # INNERMOST, so request flow is: CORS -> RequestID -> RateLimit -> app.
    # RateLimit sits inside CORS (so a 429 carries CORS headers and the
    # browser can read it) and after RequestID (so the 429 has a request
    # ID in its body and x-request-id header).
    app.add_middleware(RateLimitMiddleware)
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

    # Structured error envelope on every error response.
    # Registered after routes; handlers apply app-wide regardless of order.
    register_exception_handlers(app)

    # Instrument FastAPI after routes and middleware are registered. This
    # creates a server span per request; combined with the tracer provider
    # installed at import time, request spans export to the configured backend.
    FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()
