import datetime as dt
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select

from lugnut.auth.deps import DB, utcnow
from lugnut.auth.routes import Reader, Writer
from lugnut.reminders.models import Reminder
from lugnut.reminders.schemas import (
    EXPIRY_EDITABLE,
    CompleteIn,
    ReminderIn,
    ReminderOut,
    to_out,
    to_row_values,
)
from lugnut.reminders.state import RANK, State, add_months, local_today
from lugnut.settings_api import get_install_settings
from lugnut.units import km_from, km_to
from lugnut.vehicles.models import Vehicle
from lugnut.vehicles.odometer import current_odometer_km
from lugnut.vehicles.schemas import effective_unit

router = APIRouter(prefix="/api")


def _get(db: DB, reminder_id: int) -> Reminder:
    r = db.get(Reminder, reminder_id)
    if r is None:
        raise HTTPException(404, "Reminder not found")
    return r


def _get_vehicle(db: DB, vehicle_id: int) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if v is None:
        raise HTTPException(404, "Vehicle not found")
    return v


def _out(db: DB, r: Reminder) -> ReminderOut:
    v = _get_vehicle(db, r.vehicle_id)
    return to_out(r, get_install_settings(db), v.distance_unit, current_odometer_km(db, v))


@router.get("/reminders")
def list_reminders(
    _: Reader,
    db: DB,
    state: State | None = None,
    vehicle_id: int | None = None,
    include_completed: Annotated[bool, Query()] = False,
) -> list[ReminderOut]:
    q = select(Reminder)
    if vehicle_id is not None:
        q = q.where(Reminder.vehicle_id == vehicle_id)
    else:  # archived vehicles stay out of the cross-vehicle list
        q = q.where(Reminder.vehicle_id.in_(select(Vehicle.id).where(Vehicle.archived.is_(False))))
    if not include_completed:
        q = q.where(Reminder.completed_at.is_(None))
    install = get_install_settings(db)
    vehicles = {v.id: v for v in db.scalars(select(Vehicle))}
    odometers = {i: current_odometer_km(db, v) for i, v in vehicles.items()}
    out = [
        to_out(r, install, vehicles[r.vehicle_id].distance_unit, odometers[r.vehicle_id])
        for r in db.scalars(q)
    ]
    if state:
        out = [r for r in out if r.state == state]
    out.sort(key=lambda r: (-RANK[r.state], r.due_date or dt.date.max, r.id))
    return out


@router.post("/vehicles/{vehicle_id}/reminders", status_code=201)
def create_reminder(vehicle_id: int, body: ReminderIn, _: Writer, db: DB) -> ReminderOut:
    v = _get_vehicle(db, vehicle_id)
    unit = effective_unit(v.distance_unit, get_install_settings(db))
    r = Reminder(**to_row_values(body, unit), vehicle_id=v.id, created_at=utcnow())
    db.add(r)
    db.commit()
    return _out(db, r)


@router.get("/reminders/{reminder_id}")
def read_reminder(reminder_id: int, _: Reader, db: DB) -> ReminderOut:
    return _out(db, _get(db, reminder_id))


@router.put("/reminders/{reminder_id}")
def replace_reminder(reminder_id: int, body: ReminderIn, _: Writer, db: DB) -> ReminderOut:
    r = _get(db, reminder_id)
    if r.kind == "expiry":
        current = _out(db, r)
        errors = [
            {
                "type": "value_error",
                "loc": ("body", k),
                "msg": "Only title, notes and warn_days can change on an expiry reminder",
                "input": v,
            }
            for k, v in body.model_dump().items()
            if k not in EXPIRY_EDITABLE and v != getattr(current, k)
        ]
        if errors:
            raise RequestValidationError(errors)
    unit = effective_unit(_get_vehicle(db, r.vehicle_id).distance_unit, get_install_settings(db))
    values = to_row_values(body, unit)
    moved_km = (values["due_km"] is None) != (r.due_km is None) or (
        values["due_km"] is not None
        and r.due_km is not None
        and abs(km_to(values["due_km"], unit) - km_to(r.due_km, unit)) > 0.05
    )
    if values["due_date"] != r.due_date or moved_km:
        r.notified_state = None  # a moved due point earns a fresh notification
    for k, val in values.items():
        setattr(r, k, val)
    db.commit()
    return _out(db, r)


@router.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: int, _: Writer, db: DB) -> None:
    db.delete(_get(db, reminder_id))
    db.commit()


@router.post("/reminders/{reminder_id}/complete")
def complete_reminder(reminder_id: int, body: CompleteIn, _: Writer, db: DB) -> ReminderOut:
    r = _get(db, reminder_id)
    if r.completed_at is not None:
        raise HTTPException(409, "Reminder already completed")
    v = _get_vehicle(db, r.vehicle_id)
    install = get_install_settings(db)
    unit = effective_unit(v.distance_unit, install)
    done = body.date or local_today(install.timezone)
    if r.repeat_months is None and r.repeat_km is None:
        r.completed_at = utcnow()
    else:
        if r.repeat_months is not None:
            r.due_date = add_months(done, r.repeat_months)
        if r.repeat_km is not None:
            # ponytail: with no odometer given or recorded, the km target stays put
            odo = current_odometer_km(db, v) if body.odometer is None else None
            base = km_from(body.odometer, unit) if body.odometer is not None else odo
            if base is not None:
                r.due_km = base + r.repeat_km
        r.notified_state = None
    db.commit()
    return _out(db, r)
