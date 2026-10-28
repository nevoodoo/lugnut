import datetime as dt
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select

from lugnut.auth.deps import DB, utcnow
from lugnut.auth.routes import Reader, Writer
from lugnut.records.models import JobType, Record
from lugnut.records.schemas import (
    RecordIn,
    RecordOut,
    RecordType,
    to_line_items,
    to_out,
    to_row_values,
)
from lugnut.settings_api import get_install_settings
from lugnut.vehicles.models import Vehicle

router = APIRouter(prefix="/api")


def _get(db: DB, record_id: int) -> Record:
    r = db.get(Record, record_id)
    if r is None:
        raise HTTPException(404, "Record not found")
    return r


def _get_vehicle(db: DB, vehicle_id: int) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if v is None:
        raise HTTPException(404, "Vehicle not found")
    return v


def _check_job_types(db: DB, body: RecordIn) -> None:
    items = to_line_items(body)
    wanted = {li.job_type_id for li in items}
    found = set(db.scalars(select(JobType.id).where(JobType.id.in_(wanted))))
    errors = [
        {
            "type": "value_error",
            "loc": ("body", "details", "line_items", i, "job_type_id"),
            "msg": "Unknown job type",
            "input": li.job_type_id,
        }
        for i, li in enumerate(items)
        if li.job_type_id is not None and li.job_type_id not in found
    ]
    if errors:
        raise RequestValidationError(errors)


@router.get("/vehicles/{vehicle_id}/records")
def list_records(
    vehicle_id: int,
    _: Reader,
    db: DB,
    type: RecordType | None = None,
    from_: Annotated[dt.date | None, Query(alias="from")] = None,
    to: dt.date | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RecordOut]:
    _get_vehicle(db, vehicle_id)
    q = select(Record).where(Record.vehicle_id == vehicle_id)
    if type:
        q = q.where(Record.type == type)
    if from_:
        q = q.where(Record.date >= from_)
    if to:
        q = q.where(Record.date <= to)
    q = q.order_by(Record.date.desc().nulls_last(), Record.id.desc()).limit(limit).offset(offset)
    install = get_install_settings(db)
    return [to_out(r, install) for r in db.scalars(q)]


@router.post("/vehicles/{vehicle_id}/records", status_code=201)
def create_record(vehicle_id: int, body: RecordIn, _: Writer, db: DB) -> RecordOut:
    v = _get_vehicle(db, vehicle_id)
    _check_job_types(db, body)
    install = get_install_settings(db)
    now = utcnow()
    r = Record(
        **to_row_values(body, install, v.distance_unit),
        vehicle=v,
        line_items=to_line_items(body),
        created_at=now,
        updated_at=now,
    )
    db.add(r)
    db.commit()
    return to_out(r, install)


@router.get("/records/{record_id}")
def read_record(record_id: int, _: Reader, db: DB) -> RecordOut:
    return to_out(_get(db, record_id), get_install_settings(db))


@router.put("/records/{record_id}")
def replace_record(record_id: int, body: RecordIn, _: Writer, db: DB) -> RecordOut:
    r = _get(db, record_id)
    _check_job_types(db, body)
    install = get_install_settings(db)
    for k, val in to_row_values(body, install, r.vehicle.distance_unit).items():
        setattr(r, k, val)
    r.line_items = to_line_items(body)
    r.updated_at = utcnow()
    db.commit()
    return to_out(r, install)


@router.delete("/records/{record_id}", status_code=204)
def delete_record(record_id: int, _: Writer, db: DB) -> None:
    db.delete(_get(db, record_id))
    db.commit()
