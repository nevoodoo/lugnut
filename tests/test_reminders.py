from dataclasses import dataclass
from datetime import date

import pytest
from conftest import CSRF

from lugnut.reminders.models import Reminder
from lugnut.reminders.state import add_months, due_state


@dataclass
class R:
    due_date: date | None = None
    due_km: float | None = None
    warn_days: int = 30
    warn_km: float = 1000


def post_reminder(client, vehicle_id, payload):
    r = client.post(f"/api/vehicles/{vehicle_id}/reminders", json=payload, headers=CSRF)
    assert r.status_code == 201, r.text
    return r.json()


def complete(client, reminder_id, payload):
    r = client.post(f"/api/reminders/{reminder_id}/complete", json=payload, headers=CSRF)
    assert r.status_code == 200, r.text
    return r.json()


def test_add_months_clamps_month_end():
    # catches: repeats landing on invalid dates or skipping months
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)
    assert add_months(date(2027, 1, 31), 1) == date(2027, 2, 28)
    assert add_months(date(2026, 11, 30), 3) == date(2027, 2, 28)


def test_more_urgent_of_date_and_distance_wins():
    # catches: a km-overdue reminder hidden because its date is far away
    r = R(due_date=date(2027, 6, 1), due_km=150_000, warn_days=30, warn_km=1000)
    assert due_state(r, date(2026, 10, 28), odometer_km=150_200) == "overdue"
    assert due_state(r, date(2027, 5, 15), odometer_km=100_000) == "soon"
    assert due_state(r, date(2026, 10, 28), odometer_km=None) == "ok"


def test_completing_repeating_reminder_advances_both(client, vehicle):
    # catches: repeat counted from the old due date, or km repeat ignored
    r = post_reminder(
        client,
        vehicle,
        {
            "title": "Service",
            "due_date": "2026-10-01",
            "due_km": 140000,
            "repeat_months": 12,
            "repeat_km": 10000,
        },
    )
    done = complete(client, r["id"], {"date": "2026-10-21", "odometer": 141180})
    assert (done["due_date"], done["due_km"]) == ("2027-10-21", 151180)


def test_put_moving_due_resets_notification(client, vehicle, db_session):
    # catches: a rescheduled reminder staying silent, or a no-op PUT re-notifying
    r = post_reminder(client, vehicle, {"title": "Rego", "due_date": "2026-10-20"})
    row = db_session.get(Reminder, r["id"])
    row.notified_state = "overdue"
    db_session.commit()
    body = client.get(f"/api/reminders/{r['id']}").json()
    client.put(f"/api/reminders/{r['id']}", json=body, headers=CSRF)
    db_session.refresh(row)
    assert row.notified_state == "overdue"
    client.put(f"/api/reminders/{r['id']}", json={**body, "due_date": "2026-12-01"}, headers=CSRF)
    db_session.refresh(row)
    assert row.notified_state is None


def test_complete_on_miles_vehicle_converts_odometer(client, logged_in):
    # catches: an odometer or repeat in miles being stored or added as km
    v = client.post(
        "/api/vehicles", json={"name": "Yank", "distance_unit": "mi"}, headers=CSRF
    ).json()["id"]
    r = post_reminder(client, v, {"title": "Oil", "due_km": 9000, "repeat_km": 5000})
    assert round(r["warn_km"]) == 621  # the 1000 km default, shown in miles
    done = complete(client, r["id"], {"odometer": 10000})
    assert done["due_km"] == pytest.approx(15000)
