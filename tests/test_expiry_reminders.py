from conftest import CSRF
from test_records import post_record


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
    rem = expiry_reminders(client, vehicle)[0]
    client.put(f"/api/reminders/{rem['id']}", json={**rem, "title": "Renew soon"}, headers=CSRF)
    client.delete(f"/api/records/{new['id']}", headers=CSRF)
    left = expiry_reminders(client, vehicle)
    assert [(r["due_date"], r["title"]) for r in left] == [("2027-01-15", "Renew soon")]
    # moving the only record to another type drops the old reminder and creates the new one
    body = {**old, "type": "insurance", "details": {"expiry_date": "2027-01-15"}}
    client.put(f"/api/records/{old['id']}", json=body, headers=CSRF)
    assert [r["expiry_type"] for r in expiry_reminders(client, vehicle)] == ["insurance"]
    client.delete(f"/api/records/{old['id']}", headers=CSRF)
    assert expiry_reminders(client, vehicle) == []


def test_renewal_reopens_completed_expiry_reminder(client, vehicle):
    # catches: a renewed expiry staying hidden because its reminder was completed earlier
    post_record(client, vehicle, rego("2026-01-15", expiry="2027-01-15"))
    rem = expiry_reminders(client, vehicle)[0]
    client.post(f"/api/reminders/{rem['id']}/complete", json={}, headers=CSRF)
    assert expiry_reminders(client, vehicle) == []
    post_record(client, vehicle, rego("2027-01-10", expiry="2028-01-15"))
    assert [r["due_date"] for r in expiry_reminders(client, vehicle)] == ["2028-01-15"]
