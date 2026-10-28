from datetime import date

import pytest
from conftest import CSRF

from lugnut.reminders.notify import check_and_notify


@pytest.fixture
def vehicle(client, logged_in):
    return client.post("/api/vehicles", json={"name": "Daily"}, headers=CSRF).json()["id"]


def set_webhook(client, url):
    return client.put("/api/settings/discord", json={"url": url}, headers=CSRF)


def post_reminder(client, vehicle_id, payload):
    r = client.post(f"/api/vehicles/{vehicle_id}/reminders", json=payload, headers=CSRF)
    assert r.status_code == 201, r.text


def test_notifies_once_per_state_and_retries_failures(client, vehicle, db_session):
    # catches: hourly duplicate pings, or a failed send being marked as sent
    set_webhook(client, "https://discord.com/api/webhooks/1/abc")
    post_reminder(client, vehicle, {"title": "Rego", "due_date": "2026-10-20"})
    calls = []

    def flaky(url, payload):
        calls.append(payload)
        if len(calls) == 1:
            raise OSError("down")

    assert check_and_notify(db_session, date(2026, 10, 28), flaky) == 0
    assert check_and_notify(db_session, date(2026, 10, 28), flaky) == 1
    assert check_and_notify(db_session, date(2026, 10, 28), flaky) == 0
    assert len(calls) == 2


def test_webhook_url_is_secret_and_restricted(client, logged_in):
    # catches: leaking the webhook via the API, and SSRF to arbitrary hosts
    assert set_webhook(client, "http://169.254.169.254/x").status_code == 422
    assert set_webhook(client, "https://discord.com/api/webhooks/1/a b").status_code == 422
    assert set_webhook(client, "https://discord.com/api/webhooks/1/abc").status_code == 200
    s = client.get("/api/settings").json()
    assert s["discord_webhook_set"] is True and "abc" not in str(s)
