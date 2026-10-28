from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY = 26 * 2**20  # the 25 MiB file cap plus multipart overhead
PATH_LIMITS = {"/api/import/lubelogger": 2**30}  # exact paths only


class BodyLimit:
    """Pure-ASGI cap on request bodies. Counts bytes as they arrive, so it holds with or
    without Content-Length and fires before FastAPI parses forms or runs auth dependencies."""

    def __init__(
        self, app: ASGIApp, limit: int = MAX_BODY, path_limits: dict[str, int] = PATH_LIMITS
    ) -> None:
        self.app = app
        self.limit = limit
        self.path_limits = path_limits

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rejected = started = False
        # ponytail: matches the full scope["path"]; behind a proxy with a root_path the import
        # gets the default limit (fails closed). Strip root_path here if that setup is needed.
        limit = self.path_limits.get(scope.get("path", ""), self.limit)

        async def reject() -> None:
            nonlocal rejected
            rejected = True
            if started:  # a response is already underway; just cut the request off
                return
            body = b'{"detail":"Request too large"}'
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                        (b"connection", b"close"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})

        declared = dict(scope["headers"]).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > limit:
            await reject()
            return

        seen = 0

        async def counted_receive() -> Message:
            nonlocal seen
            if rejected:
                return {"type": "http.disconnect"}
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > limit:
                    await reject()
                    return {"type": "http.disconnect"}
            return msg

        async def guarded_send(msg: Message) -> None:
            nonlocal started
            if msg["type"] == "http.response.start":
                started = True
            if not rejected:  # the app may try to answer the disconnect; drop it
                await send(msg)

        await self.app(scope, counted_receive, guarded_send)
