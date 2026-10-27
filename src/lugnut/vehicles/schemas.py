from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from lugnut.settings_api import InstallSettings
from lugnut.timeutil import UtcDatetime
from lugnut.units import DistanceUnit, km_from, km_to
from lugnut.vehicles.models import Vehicle

FuelType = Literal["petrol", "diesel", "electric", "hybrid", "lpg"]


class VehicleIn(BaseModel):
    """PUT replaces the whole vehicle, so omitted fields reset to these defaults."""

    name: str = Field(min_length=1)
    year: int | None = None
    make: str | None = None
    model: str | None = None
    plate: str | None = None
    vin: str | None = None
    engine_number: str | None = None
    colour: str | None = None
    fuel_type: FuelType | None = None
    distance_unit: DistanceUnit | None = None
    purchase_date: date | None = None
    purchase_price: int | None = None
    sold_date: date | None = None
    sold_price: int | None = None
    odometer_adjustment: float = 0
    custom_fields: dict[str, str] = Field(default_factory=dict)
    archived: bool = False


class VehicleOut(VehicleIn):
    id: int
    odometer_adjustment: float
    distance_unit_effective: DistanceUnit
    photo_attachment_id: int | None
    created_at: UtcDatetime


def effective_unit(distance_unit: str | None, install: InstallSettings) -> DistanceUnit:
    return distance_unit or install.distance_unit  # type: ignore[return-value]


def to_row_values(body: VehicleIn, install: InstallSettings) -> dict[str, object]:
    unit = effective_unit(body.distance_unit, install)
    values = body.model_dump(exclude={"odometer_adjustment"})
    values["odometer_adjustment_km"] = km_from(body.odometer_adjustment, unit)
    return values


def to_out(v: Vehicle, install: InstallSettings) -> VehicleOut:
    unit = effective_unit(v.distance_unit, install)
    data = {c.name: getattr(v, c.name) for c in Vehicle.__table__.columns}
    km = data.pop("odometer_adjustment_km")
    return VehicleOut(**data, odometer_adjustment=km_to(km, unit), distance_unit_effective=unit)
