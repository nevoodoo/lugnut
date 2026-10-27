import pytest
from fastapi.testclient import TestClient

from lugnut import web
from lugnut.app import create_app
from lugnut.settings import Settings


@pytest.fixture
def client_with_static(tmp_path, monkeypatch):
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<!doctype html><title>Lugnut</title>")
    monkeypatch.setattr(web, "STATIC_DIR", static)
    app = create_app(Settings(data_dir=tmp_path / "data", secure_cookies=False))
    with TestClient(app) as c:
        yield c


def test_spa_fallback_and_api_404(client_with_static):
    # catches: deep-link reload breaking, or API typos returning HTML
    r = client_with_static.get("/records/5")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    r = client_with_static.get("/api/nope")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/json")


def test_static_path_traversal_blocked(client_with_static):
    # catches: reading files outside the static dir
    for path in ["/%2e%2e/%2e%2e/etc/passwd", "/assets/%2e%2e/%2e%2e/%2e%2e/etc/passwd"]:
        r = client_with_static.get(path)
        assert "root:" not in r.text
        assert r.status_code == 404 or "<title>Lugnut</title>" in r.text
