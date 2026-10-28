import pytest
from conftest import CSRF
from sqlalchemy import text

WORK_WITH_TWO_LINES = {
    "type": "work",
    "date": "2026-09-01",
    "details": {
        "category": "service",
        "line_items": [
            {"job_type_id": 1, "description": "5W-30", "cost": 8000, "quantity": 5.5},
            {"job_type_id": None, "description": "Labour", "cost": 12000, "quantity": None},
        ],
    },
}

WORK_WITH_THREE_LINES_EDITED = {  # every writable field set to a non-default value
    "type": "work",
    "date": "2026-09-02",
    "odometer": 123456,
    "cost": 45000,
    "is_estimate": True,
    "title": "90k service",
    "notes": "Booked in early",
    "tags": ["service", "dealer"],
    "custom_fields": {"booking": "B-77"},
    "details": {
        "category": "repair",
        "workshop": "Main St Motors",
        "invoice_number": "INV-1009",
        "line_items": [
            {"job_type_id": None, "description": "Labour", "cost": 15000, "quantity": 1.5},
            {"job_type_id": 5, "description": "Front pads", "cost": 22000, "quantity": 1},
            {"job_type_id": 1, "description": "5W-30", "cost": 8000, "quantity": 5.5},
        ],
    },
}

SERVER_SET = {"id", "vehicle_id", "created_at", "updated_at", "attachments"}


def strip_ids(record):
    out = {k: v for k, v in record.items() if k not in SERVER_SET}
    items = out["details"].get("line_items")
    if items is not None:
        out["details"] = {
            **out["details"],
            "line_items": [{k: v for k, v in li.items() if k != "id"} for li in items],
        }
    return out


def post_raw(client, vehicle_id, payload):
    return client.post(f"/api/vehicles/{vehicle_id}/records", json=payload, headers=CSRF)


def post_record(client, vehicle_id, payload):
    r = post_raw(client, vehicle_id, payload)
    assert r.status_code == 201, r.text
    return r.json()


def stored_volume_l(client, record_id):
    with client.app.state.engine.connect() as c:
        return c.execute(
            text("select json_extract(details, '$.volume_l') from record where id = :i"),
            {"i": record_id},
        ).scalar_one()


def _new_vehicle(client):
    return client.post("/api/vehicles", json={"name": "Daily"}, headers=CSRF).json()["id"]


@pytest.fixture
def vehicle(client, logged_in):
    return _new_vehicle(client)


@pytest.fixture
def vehicle_gal_us(client, logged_in):
    client.put("/api/settings", json={"volume_unit": "gal_us"}, headers=CSRF)
    return _new_vehicle(client)


def test_record_without_odometer_stays_null(client, vehicle):
    # catches: odometer forced or stored as 0 (spec: optional on every record)
    r = post_record(
        client, vehicle, {"type": "work", "date": "2026-10-21", "details": {"category": "repair"}}
    )
    # a field from another type must be rejected, not silently dropped
    assert (
        post_raw(
            client,
            vehicle,
            {"type": "work", "date": "2026-10-21", "details": {"category": "repair", "volume": 5}},
        ).status_code
        == 422
    )
    assert client.get(f"/api/records/{r['id']}").json()["odometer"] is None


def test_work_record_put_round_trips_line_items_and_details(client, vehicle):
    # catches: line items or details dropped/reordered on update
    r = post_record(client, vehicle, WORK_WITH_TWO_LINES)
    client.put(f"/api/records/{r['id']}", json=WORK_WITH_THREE_LINES_EDITED, headers=CSRF)
    got = client.get(f"/api/records/{r['id']}").json()
    assert strip_ids(got) == WORK_WITH_THREE_LINES_EDITED
    assert client.put(f"/api/records/{r['id']}", json=got, headers=CSRF).status_code == 200
    typo = {**got, "details": {**got["details"], "line_items": [{"descripton": "x"}]}}
    assert client.put(f"/api/records/{r['id']}", json=typo, headers=CSRF).status_code == 422


def test_fuel_volume_converted_and_required(client, vehicle_gal_us):
    # catches: fuel saved without volume, or volume unit applied wrong
    assert (
        post_raw(
            client, vehicle_gal_us, {"type": "fuel", "date": "2026-10-01", "details": {}}
        ).status_code
        == 422
    )
    r = post_record(
        client, vehicle_gal_us, {"type": "fuel", "date": "2026-10-01", "details": {"volume": 10}}
    )
    assert stored_volume_l(client, r["id"]) == pytest.approx(37.854, abs=0.001)
