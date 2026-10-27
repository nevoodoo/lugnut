from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from lugnut.auth.ratelimit import LoginLimiter
from lugnut.auth.routes import router as auth_router
from lugnut.db import get_engine
from lugnut.migrate import upgrade_database
from lugnut.records.job_types import router as job_types_router
from lugnut.records.routes import router as records_router
from lugnut.settings import Settings
from lugnut.settings_api import router as settings_router
from lugnut.vehicles.routes import router as vehicles_router
from lugnut.web import mount_frontend


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        upgrade_database(settings)
        yield
        _app.state.engine.dispose()

    app = FastAPI(title="Lugnut", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = get_engine(settings)
    app.state.login_limiter = LoginLimiter()
    app.include_router(auth_router)
    app.include_router(settings_router)
    app.include_router(vehicles_router)
    app.include_router(records_router)
    app.include_router(job_types_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": version("lugnut")}

    mount_frontend(app)  # last, so its catch-all never shadows /api routes
    return app
