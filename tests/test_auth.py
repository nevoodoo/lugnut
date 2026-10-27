import pytest

from lugnut.auth.ratelimit import LoginLimiter

U = {"username": "admin", "password": "correct horse battery"}
U2 = {"username": "intruder", "password": "another long password"}
GOOD = U
BAD = {"username": "admin", "password": "not the password"}
T = {"name": "home assistant", "scope": "write"}
cookie_auth = {"X-Lugnut": "1"}


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _make_token(client, scope):
    r = client.post("/api/tokens", json={"name": scope, "scope": scope}, headers=cookie_auth)
    assert r.status_code == 201
    return r.json()["id"], r.json()["token"]


class FakeClock:
    now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def logged_in(client):
    assert client.post("/api/setup", json=U).status_code == 201


@pytest.fixture
def write_token(client, logged_in):
    return _make_token(client, "write")


@pytest.fixture
def read_token(client, logged_in):
    return _make_token(client, "read")[1]


@pytest.fixture
def fake_clock(client, logged_in):
    clock = FakeClock()
    client.app.state.login_limiter = LoginLimiter(clock)
    return clock


def test_setup_only_once(client):
    # catches: takeover by re-running setup
    assert client.post("/api/setup", json=U).status_code == 201
    assert client.post("/api/setup", json=U2).status_code == 409


def test_revoked_token_rejected_immediately(client, write_token):
    # catches: cached auth
    tid, tok = write_token
    assert client.get("/api/auth/me", headers=bearer(tok)).status_code == 200
    client.delete(f"/api/tokens/{tid}", headers=cookie_auth)
    assert client.get("/api/auth/me", headers=bearer(tok)).status_code == 401


def test_read_token_cannot_write(client, read_token):
    # catches: scope not enforced
    r = client.post("/api/tokens", json={"name": "x", "scope": "read"}, headers=bearer(read_token))
    assert r.status_code == 403


def test_cookie_write_requires_csrf_header(client, logged_in):
    # catches: cross-site requests riding the session cookie
    assert client.post("/api/tokens", json=T).status_code == 403
    assert client.post("/api/tokens", json=T, headers={"X-Lugnut": "1"}).status_code == 201


def test_login_backoff_after_repeated_failures(client, fake_clock):
    # catches: unlimited password guessing
    for _ in range(5):
        client.post("/api/auth/login", json=BAD)
    assert client.post("/api/auth/login", json=GOOD).status_code == 429
    fake_clock.now += 1
    assert client.post("/api/auth/login", json=GOOD).status_code == 200
