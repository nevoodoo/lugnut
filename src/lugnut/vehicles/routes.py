from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from lugnut.attachments import storage
from lugnut.attachments.models import Attachment
from lugnut.auth.deps import DB, utcnow
from lugnut.auth.routes import Reader, Writer
from lugnut.settings_api import get_install_settings
from lugnut.vehicles.models import Vehicle
from lugnut.vehicles.odometer import current_odometer_km
from lugnut.vehicles.schemas import VehicleIn, VehicleOut, to_out, to_row_values

router = APIRouter(prefix="/api/vehicles")


def _get(db: DB, vehicle_id: int) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if v is None:
        raise HTTPException(404, "Vehicle not found")
    return v


@router.get("")
def list_vehicles(_: Reader, db: DB, archived: bool = False) -> list[VehicleOut]:
    install = get_install_settings(db)
    rows = db.query(Vehicle).filter(Vehicle.archived == archived).order_by(Vehicle.id).all()
    return [to_out(v, install, current_odometer_km(db, v)) for v in rows]


@router.post("", status_code=201)
def create_vehicle(body: VehicleIn, _: Writer, db: DB) -> VehicleOut:
    install = get_install_settings(db)
    v = Vehicle(**to_row_values(body, install), created_at=utcnow())
    db.add(v)
    db.commit()
    return to_out(v, install, current_odometer_km(db, v))


@router.get("/{vehicle_id}")
def read_vehicle(vehicle_id: int, _: Reader, db: DB) -> VehicleOut:
    v = _get(db, vehicle_id)
    return to_out(v, get_install_settings(db), current_odometer_km(db, v))


@router.put("/{vehicle_id}")
def replace_vehicle(vehicle_id: int, body: VehicleIn, _: Writer, db: DB) -> VehicleOut:
    v = _get(db, vehicle_id)
    install = get_install_settings(db)
    for k, val in to_row_values(body, install).items():
        setattr(v, k, val)
    db.commit()
    return to_out(v, install, current_odometer_km(db, v))


@router.delete("/{vehicle_id}", status_code=204)
def delete_vehicle(vehicle_id: int, request: Request, _: Writer, db: DB) -> None:
    v = _get(db, vehicle_id)
    # ponytail: an upload landing between select and delete is orphaned on disk; sweep if it matters
    names = list(db.scalars(select(Attachment.stored_name).where(Attachment.vehicle_id == v.id)))
    db.delete(v)
    db.commit()
    storage.delete_many(request.app.state.settings, names)
