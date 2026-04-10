"""Request ID middleware for tracing."""

import uuid

from starlette.types import ASGIApp, Receive, Scope, Send


class RequestIDMiddleware:
    """Attach a unique request ID to every request/response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", b"").decode() or str(uuid.uuid4())

        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = request_id

        async def send_with_request_id(message: dict) -> None:
            if message["type"] == "http.response.start":
                resp_headers = list(message.get("headers", []))
                resp_headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = resp_headers
            await send(message)

        await self.app(scope, receive, send_with_request_id)  # type: ignore
