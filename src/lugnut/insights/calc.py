import datetime as dt
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from statistics import median
from typing import Any, NamedTuple

from lugnut.reminders.state import add_months

SPEND_TYPES = {"fuel", "registration", "insurance", "inspection", "toll", "parking", "fine"}
OUTLIER_SEGMENTS = 5
OUTLIER_RATIO = 0.25


@dataclass(frozen=True)
class Item:
    job_type: str | None
    description: str | None
    cost: int | None


@dataclass(frozen=True)
class Row:
    type: str
    date: dt.date | None
    odometer_km: float | None
    cost: int | None
    is_estimate: bool = False
    title: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)
    items: tuple[Item, ...] = ()


@dataclass(frozen=True)
class Month:
    month: str
    total: int
    by_category: dict[str, int]


@dataclass(frozen=True)
class CostSummary:
    total: int
    by_category: dict[str, int]
    distance_km: float | None
    per_km: float | None
    missing: list[str]


@dataclass(frozen=True)
class Ownership:
    total: int | None
    running: int
    purchase_price: int | None
    sold_price: int | None
    months: int | None
    distance_km: float | None
    per_km: float | None
    missing: list[str]


@dataclass(frozen=True)
class Segment:
    date: dt.date | None
    odometer_km: float
    distance_km: float
    litres: float
    outlier: bool


@dataclass(frozen=True)
class Economy:
    segments: list[Segment]
    litres: float
    distance_km: float
    recent_litres_per_km: float | None
    skipped: int
    missing: list[str]


def category(row: Row) -> str | None:
    """Cost category of a row, or None when it does not count as money spent."""
    if row.cost is None or row.is_estimate or row.type in ("todo", "note"):
        return None
    if row.type == "work":
        return str(row.details.get("category", "service"))
    return row.type if row.type in SPEND_TYPES else "other"


class _Spend(NamedTuple):
    date: dt.date
    cost: int
    category: str
    row: Row


def _spends(rows: Sequence[Row]) -> list[_Spend]:
    out = []
    for r in rows:
        cat = category(r)
        if r.date is not None and r.cost is not None and cat is not None:
            out.append(_Spend(r.date, r.cost, cat, r))
    return out


def spend(rows: Sequence[Row]) -> list[Row]:
    return [s.row for s in _spends(rows)]


def _per_km(total: int, distance: float | None) -> float | None:
    return total / distance if distance else None


def _sum_by_category(spends: Sequence[_Spend]) -> dict[str, int]:
    out: dict[str, int] = {}
    for s in spends:
        out[s.category] = out.get(s.category, 0) + s.cost
    return out


def distance_km(rows: Sequence[Row], start: dt.date | None, end: dt.date) -> float | None:
    """Highest reading in the window minus the latest one at or before its start."""
    readings = sorted(
        (r.date, r.odometer_km)
        for r in rows
        if r.date is not None and r.odometer_km is not None and r.date <= end
    )
    before = [o for d, o in readings if start and d <= start]
    inside = [o for d, o in readings if start is None or d > start]
    if before and inside:
        return max(inside) - before[-1]
    if not before and len(inside) >= 2:
        return max(inside) - min(inside)
    return None


def monthly_costs(rows: Sequence[Row], today: dt.date, months: int = 24) -> list[Month]:
    first = add_months(today.replace(day=1), -(months - 1))
    buckets: dict[str, list[_Spend]] = {
        add_months(first, i).strftime("%Y-%m"): [] for i in range(months)
    }
    for s in _spends(rows):
        buckets.get(s.date.strftime("%Y-%m"), []).append(s)
    return [Month(k, sum(s.cost for s in b), _sum_by_category(b)) for k, b in buckets.items()]


def cost_summary(rows: Sequence[Row], start: dt.date | None, end: dt.date) -> CostSummary:
    inside = [s for s in _spends(rows) if (start is None or s.date >= start) and s.date <= end]
    total = sum(s.cost for s in inside)
    dist = distance_km(rows, start, end)
    missing = (["no_costs"] if not inside else []) + (
        ["not_enough_readings"] if dist is None else []
    )
    return CostSummary(total, _sum_by_category(inside), dist, _per_km(total, dist), missing)


def _whole_months(start: dt.date, end: dt.date) -> int:
    n = (end.year - start.year) * 12 + end.month - start.month - (end.day < start.day)
    return max(n, 1)


def ownership(
    rows: Sequence[Row],
    purchase_date: dt.date | None,
    purchase_price: int | None,
    sold_date: dt.date | None,
    sold_price: int | None,
    today: dt.date,
) -> Ownership:
    spent = _spends(rows)
    running = sum(s.cost for s in spent)
    end = sold_date or today
    start = purchase_date or min((s.date for s in spent), default=None)
    dist = distance_km(rows, None, end)
    total = None if purchase_price is None else purchase_price + running - (sold_price or 0)
    missing = (["no_purchase_price"] if total is None else []) + (
        ["not_enough_readings"] if dist is None else []
    )
    return Ownership(
        total,
        running,
        purchase_price,
        sold_price,
        _whole_months(start, end) if start else None,
        dist,
        None if total is None else _per_km(total, dist),
        missing,
    )


def economy(rows: Sequence[Row]) -> Economy:
    fills = sorted((r for r in rows if r.type == "fuel"), key=lambda r: r.date or dt.date.min)
    raw: list[tuple[dt.date | None, float, float, float]] = []
    skipped = 0
    open_odo: float | None = None
    litres = 0.0
    for r in fills:
        full = r.details.get("full_tank", True)
        odo = r.odometer_km
        if open_odo is not None:
            if odo is None or r.details.get("missed_previous") or (full and odo <= open_odo):
                skipped += 1
                open_odo = None
            else:
                litres += r.details.get("volume") or 0
                if full:
                    raw.append((r.date, odo, odo - open_odo, litres))
                    open_odo, litres = odo, 0.0
                continue
        if full and odo is not None:
            open_odo, litres = odo, 0.0
    ratios = [lt / d for _, _, d, lt in raw]
    mid = median(ratios) if len(raw) >= OUTLIER_SEGMENTS else None
    segments = [
        Segment(d, o, dist, lt, mid is not None and abs(ratio - mid) / mid > OUTLIER_RATIO)
        for (d, o, dist, lt), ratio in zip(raw, ratios, strict=True)
    ]
    recent = ratios[-5:]
    missing = ["no_fuel"] if not fills else ["not_enough_full_fills"] if not segments else []
    return Economy(
        segments,
        sum(s.litres for s in segments),
        sum(s.distance_km for s in segments),
        sum(recent) / len(recent) if len(segments) >= 2 else None,
        skipped,
        missing,
    )
