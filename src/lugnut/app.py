from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from lugnut.db import get_engine
from lugnut.migrate import upgrade_database
from lugnut.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        upgrade_database(settings)
        yield
        _app.state.engine.dispose()

    app = FastAPI(title="Lugnut", lifespan=lifespan)
    app.state.engine = get_engine(settings)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": version("lugnut")}

    return app
