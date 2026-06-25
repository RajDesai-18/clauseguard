"""Structured error envelope and exception handlers.

Every error response from the API shares a single JSON shape::

    {
        "error": {
            "code": "not_found",
            "message": "Contract not found.",
            "request_id": "…",
            "details": null
        }
    }

so the frontend can branch on a stable ``code`` instead of parsing prose,
and every error carries the request ID for log correlation.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# Map well-known HTTP status codes to stable, snake_case error codes.
# Endpoints raising a bare HTTPException get a sensible code for free;
# domain code that wants a more specific code raises AppError instead.
_STATUS_CODE_MAP: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: "payload_too_large",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "unsupported_media_type",
    status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
    status.HTTP_502_BAD_GATEWAY: "upstream_error",
    status.HTTP_503_SERVICE_UNAVAILABLE: "service_unavailable",
}

_DEFAULT_CODE = "error"
_INTERNAL_ERROR_MESSAGE = "An unexpected error occurred. Please try again."


class AppError(Exception):
    """Application error with a stable, structured response shape.

    Raise this (or a subclass) from domain/service code when you want a
    specific machine-readable ``code`` on the response. Bare
    ``HTTPException`` still works and gets a code derived from its status.

    Args:
        message: Human-readable, client-safe description.
        status_code: HTTP status to return.
        code: Stable snake_case identifier the frontend can branch on.
        details: Optional structured context (field errors, retry hints).
        headers: Optional response headers (e.g. ``Retry-After``).
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "app_error",
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        self.headers = headers


def _request_id(request: Request) -> str | None:
    """Pull the request ID stashed by RequestIDMiddleware, if present."""
    return getattr(request.state, "request_id", None)


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str | None,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the canonical error envelope as a JSONResponse."""
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details,
        }
    }
    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """Render an AppError using its explicit code and status."""
    return _error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=_request_id(request),
        details=exc.details,
        headers=exc.headers,
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Wrap a bare HTTPException into the structured envelope.

    The ``detail`` string becomes the message; the code is derived from
    the status so existing ``raise HTTPException(...)`` call sites get a
    stable code without being rewritten.
    """
    code = _STATUS_CODE_MAP.get(exc.status_code, _DEFAULT_CODE)
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return _error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        request_id=_request_id(request),
        headers=getattr(exc, "headers", None),
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Render request-validation failures as a 422 with field details."""
    details = [
        {
            "field": ".".join(str(p) for p in err.get("loc", ())),
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Request validation failed.",
        request_id=_request_id(request),
        details=details,
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions.

    Logs the full traceback server-side and returns a generic message so
    we never leak internals (stack traces, driver errors) to the client.
    """
    logger.exception("Unhandled exception (request_id=%s)", _request_id(request))
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message=_INTERNAL_ERROR_MESSAGE,
        request_id=_request_id(request),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire the structured error handlers onto the app.

    Call once from the app factory. The ``Exception`` handler becomes the
    server-error (500) handler; the rest are matched by class via MRO, so
    AppError resolves before the generic catch-all.
    """
    app.add_exception_handler(AppError, _handle_app_error)  # type: ignore
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)  # type: ignore
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore
    app.add_exception_handler(Exception, _handle_unexpected_error)
