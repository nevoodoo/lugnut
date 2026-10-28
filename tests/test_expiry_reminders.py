import pytest
from conftest import CSRF
from test_records import post_record


@pytest.fixture
def vehicle(client, logged_in):
    return client.post("/api/vehicles", json={"name": "Daily"}, headers=CSRF).json()["id"]


def rego(date, expiry):
    return {"type": "registration", "date": date, "details": {"expiry_date": expiry}}


def expiry_reminders(client, vehicle_id):
    got = client.get("/api/reminders", params={"vehicle_id": vehicle_id}).json()
    return [r for r in got if r["kind"] == "expiry"]


def test_expiry_reminder_follows_latest_record(client, vehicle):
    # catches: duplicate expiry reminders, or a stale one surviving its record
    old = post_record(client, vehicle, rego("2026-01-15", expiry="2027-01-15"))
    new = post_record(client, vehicle, rego("2027-01-10", expiry="2028-01-15"))
    rems = expiry_reminders(client, vehicle)
    assert [r["due_date"] for r in rems] == ["2028-01-15"]
    client.delete(f"/api/records/{new['id']}", headers=CSRF)
    assert [r["due_date"] for r in expiry_reminders(client, vehicle)] == ["2027-01-15"]
    client.delete(f"/api/records/{old['id']}", headers=CSRF)
    assert expiry_reminders(client, vehicle) == []
