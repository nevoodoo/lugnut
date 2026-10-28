import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lugnut.auth.deps import utcnow
from lugnut.records.models import Record
from lugnut.reminders.models import Reminder
from lugnut.settings_api import get_install_settings, load_regions

EXPIRY_TYPES = ("registration", "insurance", "inspection")


def sync_expiry(db: Session, vehicle_id: int, expiry_type: str) -> None:
    """Keep one reminder per (vehicle, type), pointing at the record with the latest expiry."""
    if expiry_type not in EXPIRY_TYPES:
        return
    expiry = func.json_extract(Record.details, "$.expiry_date")
    latest = db.scalars(
        select(Record)
        .where(Record.vehicle_id == vehicle_id, Record.type == expiry_type, expiry.is_not(None))
        .order_by(expiry.desc(), Record.id.desc())
        .limit(1)
    ).first()
    rem = db.scalars(
        select(Reminder).where(
            Reminder.vehicle_id == vehicle_id,
            Reminder.kind == "expiry",
            Reminder.expiry_type == expiry_type,
        )
    ).first()
    if latest is None:
        if rem:
            db.delete(rem)
        return
    due = dt.date.fromisoformat(latest.details["expiry_date"])
    region = load_regions()[get_install_settings(db).region]
    if rem is None:
        rem = Reminder(
            vehicle_id=vehicle_id,
            kind="expiry",
            expiry_type=expiry_type,
            warn_days=region.get("expiry_reminder_days", {}).get(expiry_type, 30),
            created_at=utcnow(),
        )
        db.add(rem)
    if rem.due_date != due:
        rem.notified_state = None
    rem.due_date = due
    rem.source_record_id = latest.id
    rem.title = f"{region.get('labels', {}).get(expiry_type, expiry_type.capitalize())} expires"
