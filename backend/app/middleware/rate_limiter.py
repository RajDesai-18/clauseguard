"""Token bucket rate limiting middleware (Redis-backed).

A pure ASGI middleware that meters requests per client IP using an
atomic Redis token bucket. Refill-and-consume runs as a single Lua
script so concurrent workers can't race on a check-then-set.

Placement: this middleware is registered *inside* CORS and *after*
RequestIDMiddleware (see ``create_app``). That ordering is deliberate:

- Inside CORS, so a 429 still carries CORS headers and the browser can
  read it (otherwise the frontend sees an opaque CORS failure).
- After RequestIDMiddleware, so the request ID is already on the scope
  and gets echoed in the 429 body and the ``x-request-id`` header.

It short-circuits with a JSONResponse rather than ``raise``-ing, because
this middleware sits outside Starlette's ExceptionMiddleware where our
registered handlers live; a raised exception here would bypass the
structured envelope. So we reproduce the same envelope inline.

Fails open: if Redis is unreachable, requests are allowed through. A
rate limiter should never take the whole API down when its backing
store hiccups.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

# Atomic token bucket. Refills based on elapsed wall-clock time, then
# consumes if enough tokens remain. Returns tokens/retry_after as strings
# so fractional values survive the Lua -> Redis -> Python number coercion
# (Redis truncates Lua numbers to integers on the way out).
#
# KEYS[1] = bucket key
# ARGV[1] = capacity        ARGV[2] = refill_rate (tokens/sec)
# ARGV[3] = now (seconds)   ARGV[4] = requested   ARGV[5] = ttl (seconds)
_TOKEN_BUCKET_LUA = """
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local bucket = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
local tokens = tonumber(bucket[1])
local ts = tonumber(bucket[2])

if tokens == nil then
  tokens = capacity
  ts = now
end

local elapsed = math.max(0, now - ts)
tokens = math.min(capacity, tokens + elapsed * refill_rate)

local allowed = 0
local retry_after = 0
if tokens >= requested then
  tokens = tokens - requested
  allowed = 1
else
  retry_after = (requested - tokens) / refill_rate
end

redis.call('HSET', KEYS[1], 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', KEYS[1], ttl)

return {allowed, tostring(tokens), tostring(retry_after)}
"""

# Paths that should never be metered: health checks (probes hammer these)
# and the API docs surfaces.
_EXEMPT_EXACT = {"/docs", "/redoc", "/openapi.json"}
_EXEMPT_SUFFIXES = ("/health",)

_RATE_LIMITED_MESSAGE = "Rate limit exceeded. Please retry shortly."


class RateLimitMiddleware:
    """Per-IP token bucket rate limiter."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._script: Any | None = None
        # Time for an empty bucket to fully refill, plus a buffer, so idle
        # buckets expire instead of lingering forever in Redis.
        refill = max(settings.rate_limit_refill_per_second, 1e-6)
        self._ttl = int(settings.rate_limit_capacity / refill) + 60

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not settings.rate_limit_enabled or scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if self._is_exempt(path):
            await self.app(scope, receive, send)
            return

        identity = self._client_identity(scope)
        key = f"ratelimit:{identity}"

        try:
            allowed, remaining, retry_after = await self._consume(key)
        except Exception as exc:
            # Fail open: never let a Redis problem 503 the whole API.
            logger.warning("Rate limiter unavailable, allowing request: %s", exc)
            await self.app(scope, receive, send)
            return

        if allowed:
            await self.app(scope, receive, send)
            return

        await self._reject(scope, send, remaining, retry_after)

    async def _consume(self, key: str) -> tuple[bool, float, float]:
        """Run the token bucket script. Returns (allowed, remaining, retry_after)."""
        client = await get_redis()
        if self._script is None:
            self._script = client.register_script(_TOKEN_BUCKET_LUA)

        result = await self._script(
            keys=[key],
            args=[
                settings.rate_limit_capacity,
                settings.rate_limit_refill_per_second,
                time.time(),
                1,  # tokens requested per call
                self._ttl,
            ],
            client=client,
        )
        allowed = bool(int(result[0]))
        remaining = float(result[1])
        retry_after = float(result[2])
        return allowed, remaining, retry_after

    async def _reject(
        self,
        scope: Scope,
        send: Send,
        remaining: float,
        retry_after: float,
    ) -> None:
        """Emit a 429 in the canonical error envelope with rate headers."""
        request_id = scope.get("state", {}).get("request_id")
        retry_seconds = max(1, math.ceil(retry_after))

        body = {
            "error": {
                "code": "rate_limited",
                "message": _RATE_LIMITED_MESSAGE,
                "request_id": request_id,
                "details": {"retry_after": retry_seconds},
            }
        }
        headers = {
            "Retry-After": str(retry_seconds),
            "X-RateLimit-Limit": str(settings.rate_limit_capacity),
            "X-RateLimit-Remaining": str(max(0, math.floor(remaining))),
        }
        response = JSONResponse(status_code=429, content=body, headers=headers)
        await response(scope, send=send, receive=_empty_receive)

    @staticmethod
    def _is_exempt(path: str) -> bool:
        """Health and docs paths bypass metering."""
        return path in _EXEMPT_EXACT or path.endswith(_EXEMPT_SUFFIXES)

    @staticmethod
    def _client_identity(scope: Scope) -> str:
        """Identify the caller by source IP.

        Uses the direct socket peer. Behind a trusted proxy (Railway,
        Vercel) this becomes the proxy IP; honouring X-Forwarded-For is a
        deploy-time concern we'll wire up when we know the proxy topology,
        since trusting that header blindly lets clients spoof identity.
        """
        client = scope.get("client")
        if client:
            return client[0]
        return "unknown"


async def _empty_receive() -> dict[str, Any]:
    """No-op receive for sending a response without consuming the body."""
    return {"type": "http.request", "body": b"", "more_body": False}
