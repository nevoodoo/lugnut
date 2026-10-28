import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from lugnut.reminders.models import Reminder
from lugnut.reminders.state import State, due_state, today
from lugnut.settings_api import InstallSettings
from lugnut.timeutil import UtcDatetime
from lugnut.units import DistanceUnit, km_from, km_to
from lugnut.vehicles.schemas import effective_unit

SERVER_FIELDS = {
    "id",
    "vehicle_id",
    "kind",
    "expiry_type",
    "source_record_id",
    "notified_state",
    "completed_at",
    "state",
    "distance_unit_effective",
    "created_at",
}
KM_FIELDS = ("due_km", "repeat_km", "warn_km")
EXPIRY_EDITABLE = {"title", "notes", "warn_days"}


class ReminderFields(BaseModel):
    title: str = Field(min_length=1)
    notes: str | None = None
    due_date: dt.date | None = None
    due_km: float | None = Field(None, ge=0, validate_default=True)  # vehicle's unit
    repeat_months: int | None = Field(None, ge=1)
    repeat_km: float | None = Field(None, gt=0)  # vehicle's unit
    warn_days: int = Field(30, ge=0)
    warn_km: float = Field(1000, ge=0)  # vehicle's unit


class ReminderIn(ReminderFields):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _drop_server_fields(cls, data: Any) -> Any:
        # A GET body must PUT back as-is, so ignore the keys the server sets.
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k not in SERVER_FIELDS}
        return data

    @field_validator("due_km")
    @classmethod
    def _due_required(cls, v: float | None, info: ValidationInfo) -> float | None:
        if v is None and info.data.get("due_date") is None:
            raise ValueError("due_date or due_km is required")
        return v


class ReminderOut(ReminderFields):
    id: int
    vehicle_id: int
    distance_unit_effective: DistanceUnit
    kind: Literal["manual", "expiry"]
    expiry_type: Literal["registration", "insurance", "inspection"] | None
    source_record_id: int | None
    notified_state: str | None
    completed_at: UtcDatetime | None
    created_at: UtcDatetime
    state: State


class CompleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: dt.date | None = None
    odometer: float | None = Field(None, ge=0)  # vehicle's unit


def to_row_values(body: ReminderIn, unit: DistanceUnit) -> dict[str, Any]:
    values = body.model_dump()
    for k in KM_FIELDS:
        if values[k] is not None:
            values[k] = km_from(values[k], unit)
    return values


def to_out(
    r: Reminder, install: InstallSettings, distance_unit: str | None, odometer_km: float | None
) -> ReminderOut:
    unit = effective_unit(distance_unit, install)
    data = {k: getattr(r, k) for k in ReminderOut.model_fields if hasattr(r, k)}
    for k in KM_FIELDS:
        if data[k] is not None:
            data[k] = km_to(data[k], unit)
    state = "ok" if r.completed_at else due_state(r, today(), odometer_km)
    return ReminderOut(**data, distance_unit_effective=unit, state=state)
