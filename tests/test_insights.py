import datetime as dt

import pytest

from lugnut.insights.calc import (
    Row,
    cost_summary,
    distance_km,
    economy,
    monthly_costs,
    ownership,
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
