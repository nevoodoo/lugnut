import datetime as dt
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from lugnut.auth.deps import DB
from lugnut.auth.routes import Reader
from lugnut.insights import calc
from lugnut.records.models import JobType, Record
from lugnut.reminders.models import Reminder
from lugnut.reminders.state import local_today
from lugnut.settings_api import get_install_settings
from lugnut.units import KM_PER_MI, DistanceUnit, VolumeUnit, km_to, l_to
from lugnut.vehicles.models import Vehicle
from lugnut.vehicles.odometer import current_odometer_km
from lugnut.vehicles.schemas import effective_unit

router = APIRouter(prefix="/api")

EconomyUnit = Literal["L/100km", "mpg", "mpg (imp)"]
Convert = Callable[[float, float], float]  # (litres, km) to the display economy value


class CostSummaryOut(BaseModel):
    total: int
    by_category: dict[str, int]
    distance: float | None
    per_distance: float | None
    missing: list[str]


class MonthOut(BaseModel):
    month: str
    total: int
    by_category: dict[str, int]


class OwnershipOut(BaseModel):
    total: int | None
    running: int
    purchase_price: int | None
    sold_price: int | None
    months: int | None
    distance: float | None
    per_distance: float | None
    per_month: int | None
    missing: list[str]


class SegmentOut(BaseModel):
    date: dt.date | None
    odometer: float
    distance: float
    volume: float
    value: float
    outlier: bool


class EconomyOut(BaseModel):
    average: float | None
    recent: float | None
    change_pct: float | None
    segments: list[SegmentOut]
    skipped: int
    missing: list[str]


class RepeatJobOut(BaseModel):
    name: str
    count: int
    last_date: dt.date | None
    last_odometer: float | None
    avg_days: float | None
    avg_distance: float | None
    avg_cost: int | None
    next_date: dt.date | None
    next_odometer: float | None


class UpcomingOut(BaseModel):
    id: int
    title: str
    projected_date: dt.date | None
    last_cost: int | None


class InsightsOut(BaseModel):
    currency: str
    distance_unit: DistanceUnit
    economy_unit: EconomyUnit
    lower_is_better: bool
    this_year: CostSummaryOut
    all_time: CostSummaryOut
    monthly: list[MonthOut]
    ownership: OwnershipOut
    economy: EconomyOut
    repeat_jobs: list[RepeatJobOut]
    upcoming: list[UpcomingOut]
    groups: list[list[int]]


def _rows(db: DB, vehicle_id: int) -> list[calc.Row]:
    q = (
        select(Record)
        .where(Record.vehicle_id == vehicle_id)
        .options(selectinload(Record.line_items))
        .order_by(Record.date, Record.id)
    )
    records = list(db.scalars(q))
    names = dict(db.execute(select(JobType.id, JobType.name)).all())
    return [
        calc.Row(
            r.type,
            r.date,
            r.odometer_km,
            r.cost,
            r.is_estimate,
            r.title,
            {**r.details, "volume": r.details.get("volume_l")},
            tuple(
                calc.Item(
                    names.get(i.job_type_id) if i.job_type_id else None, i.description, i.cost
                )
                for i in r.line_items
            ),
        )
        for r in records
    ]


def _distance(km: float | None, unit: DistanceUnit) -> float | None:
    return None if km is None else km_to(km, unit)


def _per_distance(per_km: float | None, unit: DistanceUnit) -> float | None:
    return None if per_km is None else per_km * (KM_PER_MI if unit == "mi" else 1)


def _summary(s: calc.CostSummary, unit: DistanceUnit) -> CostSummaryOut:
    return CostSummaryOut(
        total=s.total,
        by_category=s.by_category,
        distance=_distance(s.distance_km, unit),
        per_distance=_per_distance(s.per_km, unit),
        missing=s.missing,
    )


def _economy_fn(unit: DistanceUnit, volume_unit: VolumeUnit) -> tuple[EconomyUnit, Convert]:
    if unit == "km":
        return "L/100km", lambda litres, km: 100 * litres / km
    gal: VolumeUnit = "gal_imp" if volume_unit == "gal_imp" else "gal_us"
    label: EconomyUnit = "mpg (imp)" if gal == "gal_imp" else "mpg"
    return label, lambda litres, km: (km / KM_PER_MI) / l_to(litres, gal)


def _economy(
    e: calc.Economy, unit: DistanceUnit, volume_unit: VolumeUnit, convert: Convert
) -> EconomyOut:
    average = convert(e.litres, e.distance_km) if e.distance_km else None
    recent = None if e.recent_litres_per_km is None else convert(e.recent_litres_per_km, 1.0)
    change = None if average is None or recent is None else (recent - average) / average * 100
    return EconomyOut(
        average=average,
        recent=recent,
        change_pct=None if change is None else round(change, 1),
        segments=[
            SegmentOut(
                date=s.date,
                odometer=km_to(s.odometer_km, unit),
                distance=km_to(s.distance_km, unit),
                volume=l_to(s.litres, volume_unit),
                value=convert(s.litres, s.distance_km),
                outlier=s.outlier,
            )
            for s in e.segments
        ],
        skipped=e.skipped,
        missing=e.missing,
    )


@router.get("/vehicles/{vehicle_id}/insights")
def get_insights(_: Reader, db: DB, vehicle_id: int) -> InsightsOut:
    v = db.get(Vehicle, vehicle_id)
    if v is None:
        raise HTTPException(404, "Vehicle not found")
    install = get_install_settings(db)
    unit = effective_unit(v.distance_unit, install)
    today = local_today(install.timezone)
    rows = _rows(db, v.id)
    reminders = [
        calc.Due(r.id, r.title, r.kind, r.expiry_type, r.due_date, r.due_km)
        for r in db.scalars(
            select(Reminder).where(Reminder.vehicle_id == v.id, Reminder.completed_at.is_(None))
        )
    ]
    own = calc.ownership(rows, v.purchase_date, v.purchase_price, v.sold_date, v.sold_price, today)
    label, convert = _economy_fn(unit, install.volume_unit)
    soon, groups = calc.upcoming(reminders, rows, today, current_odometer_km(db, v))
    return InsightsOut(
        currency=install.currency,
        distance_unit=unit,
        economy_unit=label,
        lower_is_better=label == "L/100km",
        this_year=_summary(calc.cost_summary(rows, today.replace(month=1, day=1), today), unit),
        all_time=_summary(calc.cost_summary(rows, None, today), unit),
        monthly=[MonthOut(**m.__dict__) for m in calc.monthly_costs(rows, today)],
        ownership=OwnershipOut(
            total=own.total,
            running=own.running,
            purchase_price=own.purchase_price,
            sold_price=own.sold_price,
            months=own.months,
            distance=_distance(own.distance_km, unit),
            per_distance=_per_distance(own.per_km, unit),
            per_month=None
            if own.total is None or not own.months
            else round(own.total / own.months),
            missing=own.missing,
        ),
        economy=_economy(calc.economy(rows), unit, install.volume_unit, convert),
        repeat_jobs=[
            RepeatJobOut(
                name=j.name,
                count=j.count,
                last_date=j.last_date,
                last_odometer=_distance(j.last_odometer_km, unit),
                avg_days=j.avg_days,
                avg_distance=_distance(j.avg_km, unit),
                avg_cost=j.avg_cost,
                next_date=j.next_date,
                next_odometer=_distance(j.next_km, unit),
            )
            for j in calc.repeat_jobs(rows)
        ],
        upcoming=[UpcomingOut(**u.__dict__) for u in soon],
        groups=groups,
    )
