import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

# Build output of `npm run build` in frontend/. Tests point this at a temp dir.
STATIC_DIR = Path(__file__).parent / "static"

_IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}
_NO_CACHE = {"Cache-Control": "no-cache"}


def mount_frontend(app: FastAPI) -> None:
    """Serve the built SPA, falling back to index.html for client-side routes."""
    root = STATIC_DIR.resolve()
    if not (root / "index.html").is_file():
        return  # dev without a build: `/` simply 404s

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not found")
        full = os.path.normpath(os.path.join(root, path))
        inside = full.startswith(str(root) + os.sep)
        is_file = inside and os.path.isfile(full)
        # A missing hashed asset (stale deploy) must 404, not get index.html.
        if path.startswith("assets/") and not is_file:
            raise HTTPException(404, "Not found")
        if is_file:
            hashed = full.startswith(str(root / "assets") + os.sep)
            return FileResponse(full, headers=_IMMUTABLE if hashed else _NO_CACHE)
        return FileResponse(root / "index.html", headers=_NO_CACHE)
