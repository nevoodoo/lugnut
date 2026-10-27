from conftest import CSRF


def test_timestamps_are_utc_with_z(client, logged_in):
    # catches: naive datetimes reaching the API (spec: ISO dates, unambiguous)
    client.post("/api/tokens", json={"name": "x", "scope": "read"}, headers=CSRF)
    assert client.get("/api/tokens").json()[0]["created_at"].endswith("Z")


def test_region_switch_fills_defaults_but_keeps_explicit_fields(client, logged_in):
    # catches: one settings source getting half-applied
    client.put("/api/settings", json={"region": "us", "currency": "AUD"}, headers=CSRF)
    s = client.get("/api/settings").json()
    assert (s["distance_unit"], s["currency"]) == ("mi", "AUD")
