"""Import a LubeLogger backup: upload (extract and plan), preview with options, commit."""

import json
import logging
import os
import re
import secrets
import shutil
import time
from collections import Counter
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from lugnut.attachments import storage
from lugnut.attachments.models import Attachment
from lugnut.attachments.routes import add_attachment
from lugnut.auth.deps import DB
from lugnut.auth.routes import Writer
from lugnut.lubelogger import archive
from lugnut.lubelogger.litedb import LiteDBError, read_collections
from lugnut.lubelogger.mapper import ImportPlan, build_plan
from lugnut.records.models import Record
from lugnut.records.routes import insert_record
from lugnut.records.schemas import RecordIn
from lugnut.reminders.models import Reminder
from lugnut.reminders.routes import insert_reminder
from lugnut.reminders.schemas import ReminderIn
from lugnut.settings import Settings
from lugnut.settings_api import get_install_settings
from lugnut.vehicles.models import Vehicle
from lugnut.vehicles.routes import insert_vehicle
from lugnut.vehicles.schemas import VehicleIn

router = APIRouter(prefix="/api/import/lubelogger")
log = logging.getLogger(__name__)
SOURCE = "lubelogger"
TOKEN = re.compile(r"[0-9a-f]{32}")
FILE_REF = re.compile(r"(documents|images)/[^/]+")
MAX_AGE_SECONDS = 24 * 3600
PLAN_ONLY_KEYS = ("source_id", "source_mileage", "files")


class ImportOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_order: Literal["DMY", "MDY", "YMD"] | None = None
    source_timezone: str | None = None
    tax_types: dict[str, Literal["registration", "insurance"]] = {}

    @field_validator("source_timezone")
    @classmethod
    def _known_zone(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                ZoneInfo(v)
            except (ZoneInfoNotFoundError, ValueError, OSError):
                raise ValueError(f"Unknown timezone {v!r}") from None
        return v


def _bad_file(msg: str) -> RequestValidationError:
    return RequestValidationError(
        [{"type": "value_error", "loc": ("body", "file"), "msg": msg, "input": None}]
    )


def sweep_imports(settings: Settings) -> None:
    """Remove import dirs older than a day: abandoned uploads."""
    root = settings.imports_dir
    if not root.is_dir():
        return
    cutoff = time.time() - MAX_AGE_SECONDS
    for p in root.iterdir():
        try:
            if p.stat().st_mtime < cutoff:
                shutil.rmtree(p) if p.is_dir() else p.unlink()
        except OSError:
            log.exception("could not remove old import %s", p.name)


def _import_dir(settings: Settings, token: str) -> str:
    base = str(settings.imports_dir.resolve()) + os.sep
    full = os.path.normpath(os.path.join(base, token))
    if not full.startswith(base) or not TOKEN.fullmatch(token) or not os.path.isdir(full):
        raise HTTPException(404, "Import not found; upload the backup again")
    os.utime(full)  # in use, so the 24-hour sweep leaves it alone
    return full


def _load_plan(d: str, opts: ImportOptions) -> ImportPlan:
    with open(os.path.join(d, "data", "cartracker.db"), "rb") as f:
        raw = f.read()
    try:
        cols = read_collections(raw)
    except LiteDBError as e:
        raise _bad_file(str(e)) from None
    config: Any = {}
    cfg = os.path.join(d, "config", "userConfig.json")
    if os.path.isfile(cfg):
        try:
            with open(cfg, "rb") as f:
                config = json.load(f)
        except ValueError:
            raise _bad_file("config/userConfig.json is not valid JSON") from None
        if not isinstance(config, dict):
            raise _bad_file("config/userConfig.json is not a JSON object")
    return build_plan(cols, config, opts.model_dump(exclude_none=True))


def _preview(token: str, plan: ImportPlan) -> dict[str, Any]:
    summary = [
        {
            "source_id": pv.source_id,
            "name": pv.vehicle["name"],
            "counts": {**Counter(r["type"] for r in pv.records), "reminders": len(pv.reminders)},
        }
        for pv in plan.vehicles
    ]
    return {
        "token": token,
        "summary": summary,
        "warnings": plan.warnings,
        "skipped": plan.skipped,
        "guesses": plan.guesses,
        "tax_choices": plan.tax_choices,
        "estimates": plan.estimates,
    }


@router.post("")
def upload_backup(file: UploadFile, request: Request, _: Writer) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    sweep_imports(settings)
    settings.imports_dir.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(16)
    d = os.path.join(str(settings.imports_dir.resolve()), token)
    os.mkdir(d)
    try:
        archive.extract(file.file, d)
        plan = _load_plan(d, ImportOptions())
    except archive.ArchiveError as e:
        shutil.rmtree(d, ignore_errors=True)
        if e.status == 413:
            raise HTTPException(413, str(e)) from None
        raise _bad_file(str(e)) from None
    except BaseException:
        shutil.rmtree(d, ignore_errors=True)
        raise
    return _preview(token, plan)


@router.post("/{token}/preview")
def preview_backup(token: str, body: ImportOptions, request: Request, _: Writer) -> dict[str, Any]:
    d = _import_dir(request.app.state.settings, token)
    return _preview(token, _load_plan(d, body))


@router.post("/{token}/commit")
def commit_backup(
    token: str, body: ImportOptions, request: Request, _: Writer, db: DB
) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    d = _import_dir(settings, token)
    work = d + ".committing"
    try:
        os.rename(d, work)  # claims the upload, so a second commit of it gets a 409
    except OSError:
        raise HTTPException(409, "This backup is already being imported") from None
    staged: list[str] = []  # files copied into storage, removed again if the commit fails
    try:
        plan = _load_plan(work, body)
        result = _Commit(db, settings, work, plan, staged).run()
        db.commit()
    except BaseException:
        db.rollback()
        storage.delete_many(settings, staged)
        os.rename(work, d)  # leave it for a retry
        raise
    shutil.rmtree(work, ignore_errors=True)
    return result


def _norm(v: Any) -> str:
    return "".join(str(v or "").split()).upper()


class _Commit:
    """Writes a plan through the normal create helpers. Adds only what is new; never updates."""

    def __init__(
        self, db: Session, settings: Settings, d: str, plan: ImportPlan, staged: list[str]
    ) -> None:
        self.db, self.settings, self.plan, self.staged = db, settings, plan, staged
        self.base = d + os.sep
        self.install = get_install_settings(db)
        # Fuel volumes in the plan are in the source's unit; the record helper converts from it.
        self.src_install = self.install.model_copy(update={"volume_unit": plan.volume_unit})
        self.created = dict.fromkeys(("vehicles", "records", "reminders", "attachments"), 0)
        self.existing = dict.fromkeys(("vehicles", "records", "reminders"), 0)
        self.warnings = list(plan.warnings)

    def warn(self, msg: str) -> None:
        if msg not in self.warnings:
            self.warnings.append(msg)

    def invalid(self, source_id: str, e: ValidationError) -> None:
        err = e.errors()[0]
        where = ".".join(str(x) for x in err["loc"])
        self.warn(f"{source_id}: skipped, {where}: {err['msg']}")

    def attach(
        self, ref: dict[str, str], vehicle_id: int, record_id: int | None
    ) -> Attachment | None:
        name, zip_path = ref.get("name") or "file", ref.get("zip_path") or ""
        full = os.path.normpath(os.path.join(self.base, zip_path))
        if (
            not full.startswith(self.base)
            or not FILE_REF.fullmatch(zip_path)
            or not os.path.isfile(full)
        ):
            self.warn(f"File {name!r} is missing from the backup; skipped")
            return None
        try:
            with open(full, "rb") as f:
                a = add_attachment(self.db, self.settings, f, name, vehicle_id, record_id)
        except HTTPException as e:
            self.warn(f"File {name!r} skipped: {e.detail}")
            return None
        self.staged.append(a.stored_name)
        self.created["attachments"] += 1
        return a

    def match_vehicle(self, source_id: str, planned: dict[str, Any]) -> Vehicle | None:
        """A vehicle imported earlier with this source_id that is the same car.

        source_id alone isn't enough: ids restart at 1 in every LubeLogger install. The car is the
        same when the plate or VIN matches; with neither on both sides, source_id decides."""
        rows = self.db.scalars(
            select(Vehicle).where(Vehicle.source == SOURCE, Vehicle.source_id == source_id)
        )
        for v in rows:
            pairs = [(_norm(getattr(v, k)), _norm(planned.get(k))) for k in ("plate", "vin")]
            compared = [a == b for a, b in pairs if a and b]
            if not compared or any(compared):
                return v
        return None

    def run(self) -> dict[str, Any]:
        db = self.db
        for pv in self.plan.vehicles:
            v = self.match_vehicle(pv.source_id, pv.vehicle)
            if v is not None:
                self.existing["vehicles"] += 1
            else:
                try:
                    vbody = VehicleIn(**pv.vehicle)
                except ValidationError as e:
                    self.invalid(pv.source_id, e)
                    continue
                v = insert_vehicle(db, vbody, self.install, source=SOURCE, source_id=pv.source_id)
                self.created["vehicles"] += 1
                if pv.photo_zip_path:
                    photo = self.attach(
                        {"name": "photo", "zip_path": pv.photo_zip_path}, v.id, None
                    )
                    if photo is not None and photo.content_type.startswith("image/"):
                        db.flush()
                        v.photo_attachment_id = photo.id
                    elif photo is not None:
                        self.warn(f"{pv.vehicle['name']}: photo is not an image; kept as a file")
            unit = pv.vehicle["distance_unit"]  # the plan's distances are in this unit
            # LubeLogger ids restart in every install, so "already imported" is per vehicle
            seen_records = set(
                db.scalars(
                    select(Record.source_id).where(
                        Record.vehicle_id == v.id, Record.source == SOURCE
                    )
                )
            )
            seen_reminders = set(
                db.scalars(
                    select(Reminder.source_id).where(
                        Reminder.vehicle_id == v.id, Reminder.source == SOURCE
                    )
                )
            )
            for rec in pv.records:
                sid = rec["source_id"]
                if sid in seen_records:
                    self.existing["records"] += 1
                    continue
                try:
                    rbody = RecordIn(**{k: x for k, x in rec.items() if k not in PLAN_ONLY_KEYS})
                except ValidationError as e:
                    self.invalid(sid, e)
                    continue
                r = insert_record(
                    db, v, rbody, self.src_install, unit, source=SOURCE, source_id=sid
                )
                seen_records.add(sid)
                self.created["records"] += 1
                for ref in rec["files"]:
                    self.attach(ref, v.id, r.id)
            for rem in pv.reminders:
                sid = rem["source_id"]
                if sid in seen_reminders:
                    self.existing["reminders"] += 1
                    continue
                try:
                    mbody = ReminderIn(**{k: x for k, x in rem.items() if k != "source_id"})
                except ValidationError as e:
                    self.invalid(sid, e)
                    continue
                insert_reminder(db, v, mbody, unit, source=SOURCE, source_id=sid)
                seen_reminders.add(sid)
                self.created["reminders"] += 1
        return {
            "created": self.created,
            "skipped_existing": self.existing,
            "warnings": self.warnings,
        }
