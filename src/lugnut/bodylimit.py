from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY = 26 * 2**20  # the 25 MiB file cap plus multipart overhead


class BodyLimit:
    """Pure-ASGI cap on request bodies. Counts bytes as they arrive, so it holds with or
    without Content-Length and fires before FastAPI parses forms or runs auth dependencies."""

    def __init__(self, app: ASGIApp, limit: int = MAX_BODY) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rejected = started = False

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
        if declared.isdigit() and int(declared) > self.limit:
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
                if seen > self.limit:
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
