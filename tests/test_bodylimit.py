import asyncio

from lugnut.bodylimit import BodyLimit


def test_body_limit_never_double_starts():
    # catches: a second http.response.start when the app already answered and the body then
    # exceeds the limit
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        while (await receive())["type"] == "http.request":
            pass
        await send({"type": "http.response.body", "body": b"ok"})

    sent = []
    msgs = iter([{"type": "http.request", "body": b"x" * 20, "more_body": True}] * 2)

    async def send(m):
        sent.append(m["type"])

    async def receive():
        return next(msgs)

    asyncio.run(BodyLimit(app, limit=10)({"type": "http", "headers": []}, receive, send))
    assert sent.count("http.response.start") == 1
