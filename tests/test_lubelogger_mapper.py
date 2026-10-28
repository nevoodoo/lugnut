import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from lugnut.lubelogger.litedb import read_collections
from lugnut.lubelogger.mapper import build_plan

FIXTURE = Path(__file__).parent / "fixtures" / "lubelogger_demo.zip"


def test_plan_maps_demo_backup():
    # catches: wrong category/type mapping, unit and date conversion, odometer 0 kept
    with zipfile.ZipFile(FIXTURE) as zf:
        cols = read_collections(zf.read("data/cartracker.db"))
        config = json.loads(zf.read("config/userConfig.json"))
    cols["servicerecords"].append({**cols["servicerecords"][0], "_id": 999, "Mileage": 0})
    cols["gasrecords"].append({**cols["gasrecords"][0], "_id": 998, "Gallons": "x", "Cost": "abc"})
    cols["vehicles"][0]["PurchaseDate"] = "garbage"
    plan = build_plan(cols, config, {})
    assert plan.skipped["gasrecords"] == 1
    assert [w for w in plan.warnings if w.startswith("gasrecords 998: skipped")]
    assert "Vehicle PurchaseDate 'garbage' couldn't be read; left blank" in plan.warnings
    v = plan.vehicles[0]
    assert v.vehicle["name"] == "1992 Jeep Cherokee"
    assert v.vehicle["distance_unit"] == "mi" and v.vehicle["fuel_type"] == "petrol"
    assert v.photo_zip_path == "images/a5fc022e-3d82-40d0-94bc-33ed07f19bfb.jpg"
    assert plan.volume_unit == "gal_us"  # UseMPG without UseUKMPG
    assert len(v.records) == 109 + 110 + 34 + 22 + 1 + 13 + 3
    assert {r["details"]["category"] for r in v.records if r["type"] == "work"} == {
        "service",
        "repair",
        "upgrade",
    }
    fuel = next(r for r in v.records if r["source_id"] == "gasrecords:2")
    assert fuel["details"] == {"volume": 11.913, "full_tank": True, "missed_previous": False}
    assert (fuel["cost"], str(fuel["date"])) == (2572, "2020-05-30")
    zero = next(r for r in v.records if r["source_id"] == "servicerecords:999")
    assert zero["odometer"] is None and zero["source_mileage"] == 0
    assert (
        next(r for r in v.records if r["source_id"] == "odometerrecords:59")["odometer"] == 215393
    )
    tax = next(r for r in v.records if r["source_id"] == "taxrecords:1")
    assert tax["type"] == "registration" and tax["details"]["expiry_date"] is None
    assert plan.skipped == {"supplyrecords": 10, "gasrecords": 1}
    (rem,) = v.reminders
    assert (rem["due_km"], rem["repeat_months"], rem["repeat_km"]) == (225000, None, 5000)
    assert plan.guesses["source_timezone"] == "UTC"
    # the demo's times sit at 00:00, 06:00 and 07:00 UTC: no single offset fits
    assert any(w.startswith("Dates in this backup don't line up with UTC") for w in plan.warnings)
    # Sydney local midnight is 13:00Z in summer and 14:00Z in winter (DST ends 2020-04-05)
    syd = [datetime(2020, 3, 1, 13, tzinfo=UTC), datetime(2020, 5, 1, 14, tzinfo=UTC)]
    small = {
        "vehicles": [{"_id": 1, "Year": 2010, "Make": "Ford", "Model": "Falcon"}],
        "odometerrecords": [
            {"_id": i, "VehicleId": 1, "Date": d, "Mileage": 100 * i} for i, d in enumerate(syd, 1)
        ],
    }
    p = build_plan(small, {}, {"install_timezone": "Australia/Sydney"})
    assert p.guesses["source_timezone"] == "Australia/Sydney"
    assert not [w for w in p.warnings if "Dates" in w]
    assert [str(r["date"]) for r in p.vehicles[0].records] == ["2020-03-02", "2020-05-02"]
