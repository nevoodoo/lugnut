import datetime as dt
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from lugnut.records.models import LineItem, Record
from lugnut.settings_api import InstallSettings
from lugnut.timeutil import UtcDatetime
from lugnut.units import km_from, km_to, l_from, l_to
from lugnut.vehicles.schemas import effective_unit

RecordType = Literal[
    "work",
    "fuel",
    "odometer",
    "registration",
    "insurance",
    "inspection",
    "toll",
    "parking",
    "fine",
    "todo",
    "note",
]
UNDATED = {"todo", "note"}
SERVER_FIELDS = {"id", "vehicle_id", "created_at", "updated_at"}


class LineItemFields(BaseModel):
    job_type_id: int | None = None
    description: str | None = None
    cost: int | None = None
    quantity: float | None = None


class LineItemIn(LineItemFields):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _drop_id(cls, data: Any) -> Any:
        # A GET body must PUT back as-is, so ignore the key the server sets.
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k != "id"}
        return data


class LineItemOut(LineItemFields):
    id: int


class Details(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a field from another type is a 422, not dropped


class WorkDetails(Details):
    category: Literal["service", "repair", "upgrade"]
    workshop: str | None = None
    invoice_number: str | None = None
    line_items: list[LineItemIn] = Field(default_factory=list)  # stored in line_item


class FuelDetails(Details):
    volume: float | None = Field(None, gt=0)  # install volume unit in the API, litres in the DB
    full_tank: bool = True
    missed_previous: bool = False
    charge_start_pct: float | None = Field(None, ge=0, le=100)
    charge_end_pct: float | None = Field(None, ge=0, le=100)

    @model_validator(mode="after")
    def _volume_or_charge(self) -> "FuelDetails":
        if self.volume is None and self.charge_end_pct is None:
            raise ValueError("volume is required unless charge_end_pct is set")
        return self


class NoDetails(Details):
    pass


class RegistrationDetails(Details):
    plate: str | None = None
    expiry_date: dt.date | None = None
    period_months: int | None = Field(None, ge=1)


class InsuranceDetails(Details):
    insurer: str | None = None
    policy_number: str | None = None
    start_date: dt.date | None = None
    expiry_date: dt.date | None = None
    excess: int | None = None
    excess_notes: str | None = None


class InspectionDetails(Details):
    result: Literal["pass", "fail", "advisory"] | None = None
    expiry_date: dt.date | None = None
    inspector: str | None = None


class LocationDetails(Details):
    location: str | None = None


class FineDetails(Details):
    offence: str | None = None
    due_date: dt.date | None = None
    paid: bool = False
    reference: str | None = None


class TodoDetails(Details):
    priority: Literal["low", "medium", "high"] = "medium"
    status: Literal["backlog", "in_progress", "done"] = "backlog"
    quoted: int | None = None


class NoteDetails(Details):
    pinned: bool = False


DETAILS: dict[str, type[Details]] = {
    "work": WorkDetails,
    "fuel": FuelDetails,
    "odometer": NoDetails,
    "registration": RegistrationDetails,
    "insurance": InsuranceDetails,
    "inspection": InspectionDetails,
    "toll": LocationDetails,
    "parking": LocationDetails,
    "fine": FineDetails,
    "todo": TodoDetails,
    "note": NoteDetails,
}
assert set(DETAILS) == set(get_args(RecordType))


class RecordFields(BaseModel):
    type: RecordType
    date: dt.date | None = Field(None, validate_default=True)
    odometer: float | None = Field(None, ge=0, validate_default=True)  # vehicle's unit
    cost: int | None = None
    is_estimate: bool = False
    title: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, str] = Field(default_factory=dict)


class RecordIn(RecordFields):
    """PUT replaces the whole record, line items included."""

    model_config = ConfigDict(extra="forbid")

    details: Any = Field(default_factory=dict, validate_default=True)

    @model_validator(mode="before")
    @classmethod
    def _drop_server_fields(cls, data: Any) -> Any:
        # A GET body must PUT back as-is, so ignore the keys the server sets.
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k not in SERVER_FIELDS}
        return data

    @field_validator("date")
    @classmethod
    def _date_required(cls, v: dt.date | None, info: ValidationInfo) -> dt.date | None:
        if v is None and info.data.get("type", "note") not in UNDATED:
            raise ValueError("date is required for this record type")
        return v

    @field_validator("odometer")
    @classmethod
    def _odometer_required(cls, v: float | None, info: ValidationInfo) -> float | None:
        if v is None and info.data.get("type") == "odometer":
            raise ValueError("odometer is required for odometer records")
        return v

    @field_validator("details")
    @classmethod
    def _typed_details(cls, v: Any, info: ValidationInfo) -> Any:
        t = info.data.get("type")
        return DETAILS[t].model_validate(v) if t else v


class RecordOut(RecordFields):
    id: int
    vehicle_id: int
    details: dict[str, Any]
    created_at: UtcDatetime
    updated_at: UtcDatetime


def to_row_values(
    body: RecordIn, install: InstallSettings, distance_unit: str | None
) -> dict[str, Any]:
    unit = effective_unit(distance_unit, install)
    values = body.model_dump(exclude={"odometer", "details"})
    values["odometer_km"] = None if body.odometer is None else km_from(body.odometer, unit)
    details = body.details.model_dump(mode="json", exclude={"line_items"})
    if body.type == "fuel":
        v = details.pop("volume")
        details["volume_l"] = None if v is None else l_from(v, install.volume_unit)
    values["details"] = details
    return values


def to_line_items(body: RecordIn) -> list[LineItem]:
    items = body.details.line_items if body.type == "work" else []
    return [LineItem(position=i, **li.model_dump()) for i, li in enumerate(items)]


def to_out(r: Record, install: InstallSettings) -> RecordOut:
    unit = effective_unit(r.vehicle.distance_unit, install)
    stored = dict(r.details)
    if r.type == "fuel":
        litres = stored.pop("volume_l")
        stored["volume"] = None if litres is None else round(l_to(litres, install.volume_unit), 3)
    # Re-validate so details written before a field was added still come back complete.
    details = DETAILS[r.type].model_validate(stored).model_dump(mode="json", exclude={"line_items"})
    if r.type == "work":
        details["line_items"] = [
            LineItemOut.model_validate(li, from_attributes=True).model_dump() for li in r.line_items
        ]
    common = {k: getattr(r, k) for k in RecordOut.model_fields if k not in ("odometer", "details")}
    odometer = None if r.odometer_km is None else km_to(r.odometer_km, unit)
    return RecordOut(**common, odometer=odometer, details=details)
