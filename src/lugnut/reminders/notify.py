import asyncio
import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import date
from importlib.metadata import version
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from lugnut.reminders.models import Reminder
from lugnut.reminders.state import RANK, _by_date, _by_km, due_state, local_today
from lugnut.settings_api import get_install_settings, get_webhook_url, is_discord_webhook
from lugnut.units import km_to
from lugnut.vehicles.models import Vehicle
from lugnut.vehicles.odometer import current_odometer_km
from lugnut.vehicles.schemas import effective_unit

log = logging.getLogger(__name__)


class NotifyError(Exception):
    """Short reason only. Never carries the webhook URL."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None  # a 3xx surfaces as an HTTPError instead of being followed


def discord_send(url: str, payload: dict[str, Any]) -> None:
    if not is_discord_webhook(url):
        raise NotifyError("Not a Discord webhook URL")
    req = urllib.request.Request(  # noqa: S310 (host checked above)
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": f"lugnut/{version('lugnut')}"},
    )
    try:
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=10) as resp:
            if not 200 <= resp.status < 300:
                raise NotifyError(f"Discord returned HTTP {resp.status}")
    except NotifyError:
        raise
    except urllib.error.HTTPError as e:
        raise NotifyError(f"Discord returned HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError):
        raise NotifyError("Could not reach Discord") from None
    except OSError:
        raise NotifyError("Network error") from None
    except Exception:  # e.g. http.client.InvalidURL, whose message carries the URL
        raise NotifyError("Send failed") from None


def _fmt_date(d: Any, pattern: str) -> str:
    return (
        pattern.replace("YYYY", f"{d.year:04d}")
        .replace("MM", f"{d.month:02d}")
        .replace("DD", f"{d.day:02d}")
    )


def check_and_notify(db: Session, today: date, send: Callable[[str, dict[str, Any]], None]) -> int:
    url = get_webhook_url(db)
    if not url:
        return 0
    install = get_install_settings(db)
    sent = 0
    q = (
        select(Reminder, Vehicle)
        .join(Vehicle)
        .where(Reminder.completed_at.is_(None), Vehicle.archived.is_(False))
    )
    for r, v in db.execute(q).all():
        state = due_state(r, today, current_odometer_km(db, v))
        notify = "soon" if state == "due" else state
        if notify not in ("soon", "overdue") or notify == r.notified_state:
            continue
        label = f"{v.name} ({v.plate})" if v.plate else v.name
        odo = current_odometer_km(db, v)
        km_drives = r.due_km is not None and RANK[_by_km(r, odo)] > RANK[_by_date(r, today)]
        if r.due_date and not km_drives:
            due = _fmt_date(r.due_date, install.date_format)
        elif r.due_km is not None:
            unit = effective_unit(v.distance_unit, install)
            due = f"{km_to(r.due_km, unit):,.0f} {unit}"
        else:
            continue
        word = "overdue" if notify == "overdue" else "due soon"
        text = f"{r.title} for {label} is {word}: due {due}."
        try:
            send(url, {"content": text[:2000], "allowed_mentions": {"parse": []}})
        except Exception as e:  # noqa: BLE001  the URL must not reach the log
            log.warning("reminder %s not sent: %s", r.id, type(e).__name__)
            continue
        r.notified_state = notify
        db.commit()
        sent += 1
    return sent


# ponytail: known limits. Two app instances on one database can send
# duplicate messages. A tick holding a stale row can overwrite a concurrent PUT's notified_state
# reset. Fix with a send lock or claim row, and a re-read before the write.
def _run_once(engine: Engine) -> None:
    with Session(engine) as db:
        check_and_notify(db, local_today(get_install_settings(db).timezone), discord_send)


async def reminder_loop(engine: Engine, interval: int) -> None:
    while True:
        try:
            await asyncio.to_thread(_run_once, engine)
        except Exception:
            log.exception("reminder check failed")
        await asyncio.sleep(interval)
