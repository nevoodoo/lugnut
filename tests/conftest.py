import pytest
from fastapi.testclient import TestClient

from lugnut.app import create_app
from lugnut.settings import Settings


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(data_dir=tmp_path, secure_cookies=False))
    with TestClient(app) as c:
        yield c


CSRF = {"X-Lugnut": "1"}


@pytest.fixture
def logged_in(client):
    r = client.post("/api/setup", json={"username": "admin", "password": "correct horse battery"})
    assert r.status_code == 201
