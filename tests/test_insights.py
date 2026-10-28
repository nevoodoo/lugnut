import datetime as dt

import pytest
from conftest import CSRF

from lugnut.insights.calc import (
    Due,
    Item,
    Row,
    cost_summary,
    distance_km,
    economy,
    monthly_costs,
    ownership,
    repeat_jobs,
    upcoming,
)

D = dt.date


def fuel(day, odo, litres, full=True, missed=False, cost=None):
    return Row(
        "fuel",
        D(2026, 1, day) if day else None,
        odo,
        cost,
        details={"volume": litres, "full_tank": full, "missed_previous": missed},
    )


def test_economy_full_to_full_with_partial_fill():
    rows = [fuel(1, 1000, 40), fuel(5, 1300, 20, full=False), fuel(9, 1600, 25)]
    e = economy(rows)
    assert [(s.distance_km, s.litres) for s in e.segments] == [(600, 45)]
    assert e.litres == 45 and e.distance_km == 600 and e.skipped == 0


def test_economy_skips_unusable_fills():
    rows = [
        fuel(1, 1000, 10, full=False),  # partial first fill: nothing open yet
        fuel(2, 1100, 40),
        fuel(3, None, 20),  # no odometer: discards the open segment
        fuel(4, 1700, 30),
        fuel(5, 2200, 35, missed=True),
        fuel(6, 2600, 30),
        fuel(7, 2500, 30),  # backwards reading
        fuel(8, 3000, 40),
    ]
    e = economy(rows)
    # 1100 opens, None discards; 1700 opens, missed 2200 discards and reopens; 2200->2600 = 400;
    # 2500 is backwards, discards and reopens; 2500->3000 = 500
    assert [s.distance_km for s in e.segments] == [400, 500]
    assert e.skipped == 3


def test_economy_flags_outlier():
    rows = [fuel(i, 1000 + 500 * i, 40) for i in range(1, 7)] + [fuel(20, 4500, 80)]
    e = economy(rows)
    assert [s.outlier for s in e.segments] == [False] * 5 + [True]


def test_costs_ignore_estimates_and_handle_empty():
    rows = [
        Row("work", D(2026, 2, 1), 5000, 30000, details={"category": "service"}),
        Row("work", D(2026, 2, 2), None, 99999, is_estimate=True, details={"category": "repair"}),
        Row("todo", None, None, 5000),
        Row("fuel", D(2026, 3, 1), 5600, 8000, details={"volume": 40}),
    ]
    s = cost_summary(rows, None, D(2026, 3, 31))
    assert s.total == 38000 and s.by_category == {"service": 30000, "fuel": 8000}
    assert s.distance_km == 600 and s.per_km == pytest.approx(38000 / 600)
    empty = cost_summary([Row("note", None, None, None)], None, D(2026, 3, 31))
    assert (empty.total, empty.per_km) == (0, None)
    assert set(empty.missing) == {"no_costs", "not_enough_readings"}


def test_window_distance_uses_reading_before_start():
    rows = [
        Row("odometer", D(2025, 12, 20), 9000, None),
        Row("odometer", D(2026, 6, 1), 12000, None),
    ]
    assert distance_km(rows, D(2026, 1, 1), D(2026, 12, 31)) == 3000


def test_monthly_costs_fill_gaps():
    rows = [Row("toll", D(2026, 1, 3), None, 500), Row("parking", D(2026, 3, 9), None, 700)]
    months = monthly_costs(rows, D(2026, 3, 15), months=3)
    assert [(m.month, m.total) for m in months] == [
        ("2026-01", 500),
        ("2026-02", 0),
        ("2026-03", 700),
    ]


def test_ownership_with_sale_and_without_price():
    rows = [
        Row("fuel", D(2024, 2, 1), 10000, 5000, details={"volume": 40}),
        Row("odometer", D(2025, 1, 1), 30000, None),
    ]
    o = ownership(rows, D(2024, 1, 15), 2000000, D(2025, 1, 15), 1200000, D(2026, 1, 1))
    assert o.total == 2000000 + 5000 - 1200000 and o.months == 12 and o.distance_km == 20000
    assert ownership(rows, None, None, None, None, D(2026, 1, 1)).missing == ["no_purchase_price"]


def work(day, odo, *items, month=1, est=False):
    return Row(
        "work",
        D(2025, month, day),
        odo,
        sum(i.cost or 0 for i in items),
        is_estimate=est,
        details={"category": "service"},
        items=items,
    )


def test_repeat_jobs_intervals():
    def oil(c):
        return Item("Oil change", None, c)

    rows = [
        work(1, 10000, oil(9000), month=1),
        work(1, 15000, oil(11000), month=7),
        work(1, None, oil(None), month=12),
        work(2, 16000, Item(None, "wipers", 2000), month=8),
    ]
    [job] = repeat_jobs(rows)
    assert (job.name, job.count, job.avg_km, job.avg_cost) == ("Oil change", 3, 5000, 10000)
    assert job.avg_days == pytest.approx((181 + 153) / 2)
    assert job.next_km is None  # last occurrence has no odometer


def test_upcoming_projection_and_groups():
    today = D(2026, 1, 1)
    rows = [
        Row("odometer", D(2025, 1, 1), 10000, None),
        Row("odometer", D(2025, 12, 27), 19000, None),
        Row("registration", D(2025, 2, 1), None, 80000),
        work(1, 15000, Item("Oil change", None, 9500), month=6),
    ]
    rems = [
        Due(1, "Oil change", "manual", None, None, 19500),  # 500 km at 25 km/day
        Due(2, "Rego", "expiry", "registration", D(2026, 1, 30), None),
        Due(3, "Tyres", "manual", None, D(2026, 9, 1), None),
        Due(4, "Mystery", "manual", None, None, None),
    ]
    items, groups = upcoming(rems, rows, today, 19000)
    assert [u.id for u in items] == [1, 2, 3, 4]
    assert items[0].projected_date == D(2026, 1, 21) and items[0].last_cost == 9500
    assert items[1].last_cost == 80000 and items[3].projected_date is None
    assert groups == [[1, 2]]


def test_economy_skips_fill_without_volume():
    rows = [fuel(1, 1000, 40), fuel(2, 1200, 0), fuel(3, 1500, 30), fuel(4, 2000, 35)]
    e = economy(rows)
    assert [s.distance_km for s in e.segments] == [300, 500] and e.skipped == 1


def test_insights_api_us_units(client, logged_in):
    # catches: unit conversion slips (mpg, miles) and a missing 404
    client.put(
        "/api/settings",
        json={"distance_unit": "mi", "volume_unit": "gal_us", "currency": "USD"},
        headers=CSRF,
    )
    vid = client.post(
        "/api/vehicles", json={"name": "Daily", "purchase_price": 2000000}, headers=CSRF
    ).json()["id"]
    for day, odo, gal in [("01", 100, 10), ("10", 400, 10), ("20", 700, 12)]:
        r = client.post(
            f"/api/vehicles/{vid}/records",
            json={
                "type": "fuel",
                "date": f"2026-09-{day}",
                "odometer": odo,
                "cost": 3000,
                "details": {"volume": gal, "full_tank": True},
            },
            headers=CSRF,
        )
        assert r.status_code == 201, r.text
    r = client.get(f"/api/vehicles/{vid}/insights")
    assert r.status_code == 200
    body = r.json()
    assert body["economy_unit"] == "mpg" and body["lower_is_better"] is False
    assert body["economy"]["average"] == pytest.approx(600 / 22, rel=1e-3)
    assert body["all_time"]["distance"] == pytest.approx(600, abs=0.1)
    assert body["ownership"]["missing"] == []
    assert client.get("/api/vehicles/9999/insights").status_code == 404
