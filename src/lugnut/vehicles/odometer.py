from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lugnut.records.models import Record
from lugnut.vehicles.models import Vehicle


def current_odometer_km(db: Session, vehicle: Vehicle) -> float | None:
    """Highest recorded odometer plus the vehicle's adjustment, or None with no readings."""
    top = db.scalar(select(func.max(Record.odometer_km)).where(Record.vehicle_id == vehicle.id))
    return None if top is None else top + vehicle.odometer_adjustment_km
