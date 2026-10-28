import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
DEFAULT_WARN_KM = 1000.0  # stored in km, whatever the vehicle's unit
EXPIRY_EDITABLE = {"title", "notes", "warn_days"}


class ReminderFields(BaseModel):
    title: str = Field(min_length=1)
    notes: str | None = None
    due_date: dt.date | None = None
    due_km: float | None = Field(None, ge=0)  # vehicle's unit
    repeat_months: int | None = Field(None, ge=1)
    repeat_km: float | None = Field(None, gt=0)  # vehicle's unit
    warn_days: int = Field(30, ge=0)


class ReminderIn(ReminderFields):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _drop_server_fields(cls, data: Any) -> Any:
        # A GET body must PUT back as-is, so ignore the keys the server sets.
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k not in SERVER_FIELDS}
        return data

    warn_km: float | None = Field(None, ge=0)  # vehicle's unit; omitted means the km default

    @model_validator(mode="after")
    def _due_required(self) -> "ReminderIn":
        if self.due_km is None and self.due_date is None:
            raise ValueError("due_date or due_km is required")
        return self


class ReminderOut(ReminderFields):
    warn_km: float  # vehicle's unit
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
    if values["warn_km"] is None:
        values["warn_km"] = DEFAULT_WARN_KM
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
