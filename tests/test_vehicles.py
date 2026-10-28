import pytest
from conftest import CSRF
from sqlalchemy import text

FULL_VEHICLE = {
    "name": "Hilux",
    "year": 2019,
    "make": "Toyota",
    "model": "HiLux SR5",
    "plate": "ABC123",
    "vin": "MR0FB3CD600123456",
    "engine_number": "1GD1234567",
    "colour": "White",
    "fuel_type": "diesel",
    "distance_unit": "mi",
    "purchase_date": "2020-03-14",
    "purchase_price": 5500000,
    "sold_date": "2024-06-01",
    "sold_price": 3800000,
    "odometer_adjustment": 100,
    "custom_fields": {"rego_expiry": "2027-01-01", "key": "hook 4"},
    "archived": True,
}


def stored_adjustment_km(client, vehicle_id):
    with client.app.state.engine.connect() as c:
        return c.execute(
            text("select odometer_adjustment_km from vehicle where id = :i"), {"i": vehicle_id}
        ).scalar_one()


def test_vehicle_put_round_trips_every_field(client, logged_in):
    # catches: the LubeLogger bug where update reports success but drops fields
    v = client.post("/api/vehicles", json={"name": "Daily"}, headers=CSRF).json()
    full = FULL_VEHICLE  # every writable field set to a non-default value
    client.put(f"/api/vehicles/{v['id']}", json=full, headers=CSRF)
    got = client.get(f"/api/vehicles/{v['id']}").json()
    assert {k: got[k] for k in full} == full
    # the exact GET body must PUT back, and a PUT must not clear the photo
    png = b"\x89PNG\r\n\x1a\n" + b"\0" * 32
    att = client.post(
        f"/api/vehicles/{v['id']}/attachments",
        files={"file": ("p.png", png, "application/octet-stream")},
        headers=CSRF,
    ).json()
    client.put(f"/api/vehicles/{v['id']}/photo", json={"attachment_id": att["id"]}, headers=CSRF)
    got = client.get(f"/api/vehicles/{v['id']}").json()
    assert client.put(f"/api/vehicles/{v['id']}", json=got, headers=CSRF).status_code == 200
    after = client.get(f"/api/vehicles/{v['id']}").json()
    assert after["photo_attachment_id"] == att["id"] == got["photo_attachment_id"]
    # catches: a misspelled field silently dropped
    bad = client.put(f"/api/vehicles/{v['id']}", json={**full, "colur": "x"}, headers=CSRF)
    assert bad.status_code == 422


def test_miles_vehicle_stores_km_and_survives_region_switch(client, logged_in):
    # catches: unit conversion applied twice or to stored data
    v = client.post(
        "/api/vehicles",
        json={"name": "US", "distance_unit": "mi", "odometer_adjustment": 100},
        headers=CSRF,
    ).json()
    client.put("/api/settings", json={"region": "gb"}, headers=CSRF)
    assert client.get(f"/api/vehicles/{v['id']}").json()["odometer_adjustment"] == 100
    assert stored_adjustment_km(client, v["id"]) == pytest.approx(160.9344)
    r = client.post(
        f"/api/vehicles/{v['id']}/records",
        json={"type": "odometer", "date": "2026-10-01", "odometer": 100000},
        headers=CSRF,
    ).json()
    assert client.get(f"/api/records/{r['id']}").json()["odometer"] == 100000.0
