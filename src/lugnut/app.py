from importlib.metadata import version

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Lugnut")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": version("lugnut")}

    return app
