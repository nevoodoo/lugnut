import calendar
import datetime as dt
from datetime import date
from typing import Literal, Protocol

State = Literal["ok", "soon", "due", "overdue"]
RANK: dict[State, int] = {"ok": 0, "soon": 1, "due": 2, "overdue": 3}


class ReminderLike(Protocol):
    due_date: date | None
    due_km: float | None
    warn_days: int
    warn_km: float


def today() -> date:
    """The one clock for due states; callers pass it down so tests can pin it."""
    return dt.datetime.now(dt.UTC).date()


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def _by_date(r: ReminderLike, today: date) -> State:
    if r.due_date is None:
        return "ok"
    days = (r.due_date - today).days
    return (
        "overdue" if days < 0 else "due" if days == 0 else "soon" if days <= r.warn_days else "ok"
    )


def _by_km(r: ReminderLike, odometer_km: float | None) -> State:
    if r.due_km is None or odometer_km is None:
        return "ok"
    left = r.due_km - odometer_km
    if left < 0:
        return "overdue"
    if left <= max(r.due_km * 0.01, 50):
        return "due"
    return "soon" if left <= r.warn_km else "ok"


def due_state(r: ReminderLike, today: date, odometer_km: float | None) -> State:
    """Pure, so the routes and the scheduler share it. The more urgent of date and distance wins."""
    return max(_by_date(r, today), _by_km(r, odometer_km), key=RANK.__getitem__)
