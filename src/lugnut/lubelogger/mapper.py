"""Pure mapping from read LubeLogger collections to an import plan (no database, no files)."""

import calendar
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

Doc = dict[str, Any]

MONTHS = {
    "OneMonth": 1,
    "ThreeMonths": 3,
    "SixMonths": 6,
    "OneYear": 12,
    "TwoYears": 24,
    "ThreeYears": 36,
    "FiveYears": 60,
}
NUMBER_WORDS = {
    w: n
    for n, w in enumerate(
        "Zero One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen "
        "Fourteen Fifteen Sixteen Seventeen Eighteen Nineteen".split()
    )
} | {
    w: n * 10
    for n, w in enumerate("_ _ Twenty Thirty Forty Fifty Sixty Seventy Eighty Ninety".split())
}
WORK = {"servicerecords": "service", "collisionrecords": "repair", "upgraderecords": "upgrade"}
PRIORITY = {"Critical": "high", "Normal": "medium", "Low": "low"}
PROGRESS = {
    "Backlog": "backlog",
    "InProgress": "in_progress",
    "Testing": "in_progress",
    "Done": "done",
}
SKIPPED = ("supplyrecords", "equipmentrecords", "planrecordtemplates", "inspectionrecordtemplates")
VEHICLE_FIELDS = {"vin": "vin", "enginenumber": "engine_number", "engineno": "engine_number",
                  "engine": "engine_number", "colour": "colour", "color": "colour"}  # fmt: skip


@dataclass
class PlannedVehicle:
    source_id: str
    vehicle: dict[str, Any]
    photo_zip_path: str | None = None
    records: list[dict[str, Any]] = field(default_factory=list)
    reminders: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ImportPlan:
    vehicles: list[PlannedVehicle] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)
    guesses: dict[str, str] = field(default_factory=dict)
    tax_choices: list[dict[str, Any]] = field(default_factory=list)
    estimates: list[dict[str, Any]] = field(default_factory=list)
    volume_unit: str = "L"  # unit of fuel volumes in the plan: "L" or "gal_us"


def money(v: Any) -> int | None:
    if v is None:
        return None
    return int((Decimal(str(v)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def mileage_interval(name: str | None) -> int | None:
    """FiveThousandMiles -> 5000, OneHundredFiftyThousandMiles -> 150000."""
    total = cur = 0
    for w in re.findall(r"[A-Z][a-z]*", name or ""):
        if w in NUMBER_WORDS:
            cur += NUMBER_WORDS[w]
        elif w == "Hundred":
            cur = (cur or 1) * 100
        elif w == "Thousand":
            total, cur = total + (cur or 1) * 1000, 0
        elif w != "Miles":
            return None
    return (total + cur) or None


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _date_parts(s: Any) -> list[int] | None:
    parts = re.split(r"[/.\-]", str(s or "").strip().split()[0] if str(s or "").strip() else "")
    return [int(p) for p in parts] if len(parts) == 3 and all(p.isdigit() for p in parts) else None


def guess_date_order(strings: list[Any]) -> tuple[str, bool]:
    """Return (order, certain)."""
    parts = [p for p in map(_date_parts, strings) if p]
    if any(p[0] > 31 for p in parts):
        return "YMD", True
    if any(p[0] > 12 for p in parts):
        return "DMY", True
    if any(p[1] > 12 for p in parts):
        return "MDY", True
    return "DMY", not parts


def parse_locale_date(s: Any, order: str) -> date | None:
    p = _date_parts(s)
    if not p:
        return None
    idx = {"DMY": (2, 1, 0), "MDY": (2, 0, 1), "YMD": (0, 1, 2)}[order]
    try:
        return date(p[idx[0]], p[idx[1]], p[idx[2]])
    except ValueError:
        return None


def guess_timezone(times: list[datetime]) -> str:
    tods = {t.astimezone(UTC).time() for t in times}
    if len(tods) != 1:
        return "UTC"
    (t,) = tods
    if t.minute or t.second or t.microsecond or t.hour == 0:
        return "UTC"
    # Server midnight lands on this UTC hour, so the server is that many hours behind UTC
    # (or ahead, past 12). Etc/GMT signs are inverted.
    off = t.hour if t.hour <= 12 else t.hour - 24
    return "UTC" if off == 0 else f"Etc/GMT{'+' if off > 0 else '-'}{abs(off)}"


class _Mapper:
    def __init__(self, cols: dict[str, list[Doc]], config: Doc, options: Doc):
        self.cols, self.options = cols, options
        self.plan = ImportPlan()
        mpg, uk = bool(config.get("UseMPG")), bool(config.get("UseUKMPG"))
        self.unit = "mi" if mpg else "km"
        self.plan.volume_unit = "gal_us" if mpg and not uk else "L"
        self.tz = ZoneInfo(options.get("source_timezone") or self._guess_tz())
        self.order = options.get("date_order") or self._guess_order()
        self.plan.guesses = {"date_order": self.order, "source_timezone": self.tz.key}
        self.tax_types = options.get("tax_types") or {}
        self.skipped = self.plan.skipped

    def money(self, v: Any) -> int | None:
        try:
            return money(v)
        except ArithmeticError:
            self.warn(f"Amount '{v}' couldn't be read; left blank")
            return None

    def vdate(self, v: Doc, key: str) -> date | None:
        raw = v.get(key)
        d = parse_locale_date(raw, self.order)
        if d is None and str(raw or "").strip():
            self.warn(f"Vehicle {key} '{raw}' couldn't be read; left blank")
        return d

    def guard(self, coll: str, r: Doc, fn: Any, *args: Any) -> Any:
        try:
            return fn(*args)
        except (ValueError, TypeError, KeyError, ArithmeticError) as e:
            self.warn(f"{coll} {r.get('_id', '?')}: skipped, {type(e).__name__} {str(e)[:60]}")
            self.skip(coll)
            return None

    def warn(self, msg: str) -> None:
        if msg not in self.plan.warnings:
            self.plan.warnings.append(msg)

    def skip(self, key: str) -> None:
        self.skipped[key] = self.skipped.get(key, 0) + 1

    # guesses
    def _guess_tz(self) -> str:
        times = [
            r["Date"]
            for k in (*WORK, "gasrecords", "odometerrecords", "taxrecords", "inspectionrecords")
            for r in self.cols.get(k, [])
            if self._real(r.get("Date"))
        ]
        tz = guess_timezone(times) if times else "UTC"
        if tz == "UTC" and any(t.astimezone(UTC).time() != time() for t in times):
            self.warn(
                "Dates in this backup don't line up with UTC. Set the timezone LubeLogger ran"
                " in, or some dates may be a day out."
            )
        return tz

    def _guess_order(self) -> str:
        strs = [
            v.get(k) for v in self.cols.get("vehicles", []) for k in ("PurchaseDate", "SoldDate")
        ]
        order, certain = guess_date_order(strs)
        if not certain:
            self.warn("Vehicle purchase/sold dates are ambiguous; assumed DMY, please confirm")
        return order

    @staticmethod
    def _real(d: datetime | None) -> bool:
        # .NET MinValue/MaxValue mean "no date"; check before any timezone conversion
        return d is not None and 1 < d.year < 9999

    def day(self, d: datetime | None) -> date | None:
        return d.astimezone(self.tz).date() if d and self._real(d) else None

    # helpers
    @staticmethod
    def files(r: Doc) -> list[dict[str, str]]:
        out = []
        for f in r.get("Files") or []:
            loc = str(f.get("Location") or "")
            if loc and not loc.startswith("/defaults/"):
                out.append(
                    {"name": f.get("Name") or loc.rsplit("/", 1)[-1], "zip_path": loc.lstrip("/")}
                )
        return out

    def base(
        self, coll: str, r: Doc, rtype: str, title: str | None, details: Doc, **kw: Any
    ) -> Doc:
        notes = r.get("Notes")
        rec = {
            "type": rtype,
            "date": self.day(r.get("Date")),
            "odometer": r.get("Mileage") or None,
            "cost": self.money(r.get("Cost")),
            "is_estimate": False,
            "title": title,
            "notes": notes,
            "tags": list(r.get("Tags") or []),
            "custom_fields": {
                f["Name"]: str(f.get("Value") or "") for f in r.get("ExtraFields") or []
            },
            "details": details,
            "source_id": f"{coll}:{r['_id']}",
            "source_mileage": r.get("Mileage"),
            "files": self.files(r),
        } | kw
        if re.search("estimat", f"{notes or ''} {title or ''}", re.I):
            rec["is_estimate"] = True
            self.plan.estimates.append(
                {"source_id": rec["source_id"], "title": title, "date": rec["date"]}
            )
        return rec

    def tax_type(self, r: Doc) -> tuple[str, bool]:
        tags = " ".join(r.get("Tags") or []).lower()
        desc = str(r.get("Description") or "").lower()
        for text in (tags, desc):
            if "insur" in text:
                return "insurance", True
            if re.search(r"rego|registration|licen|ctp|vehicle tax|\bmot\b", text):
                return "registration", True
        return "registration", False

    def months(self, r: Doc, kind: str, unit_key: str, custom_key: str) -> int | None:
        name = r.get(kind)
        if name in MONTHS:
            return MONTHS[name]
        n = r.get(custom_key) or 0
        if name != "Other" or n <= 0:
            return None
        if r.get(unit_key) == "Days":
            self.warn(f"Interval of {n} days rounded to whole months")
            return max(1, round(n / 30.4))
        return int(n)

    # per vehicle
    def vehicle(self, v: Doc) -> PlannedVehicle:
        label = (
            f"Vehicle {v.get('Make') or ''} {v.get('Model') or ''}".strip() or f"Vehicle {v['_id']}"
        )
        if v.get("IsElectric"):
            self.warn(
                f"{label}: electric vehicles aren't supported; "
                "imported as petrol, fuel records skipped"
            )
        if v.get("UseHours"):
            self.warn(f"{label}: counts engine hours; they are imported as distance")
        if v.get("HasOdometerAdjustment"):
            self.warn(
                f"{label}: odometer adjustment is already applied to stored readings; Lugnut's is 0"
            )
        name = " ".join(str(p) for p in (v.get("Year"), v.get("Make"), v.get("Model")) if p)
        out: dict[str, Any] = {
            "name": name or f"Vehicle {v['_id']}",
            "year": v.get("Year") or None,
            "make": v.get("Make"),
            "model": v.get("Model"),
            "plate": v.get("LicensePlate"),
            "fuel_type": "diesel" if v.get("IsDiesel") else "petrol",
            "distance_unit": self.unit,
            "purchase_date": self.vdate(v, "PurchaseDate"),
            "purchase_price": self.money(v.get("PurchasePrice")) or None,
            "sold_date": self.vdate(v, "SoldDate"),
            "sold_price": self.money(v.get("SoldPrice")) or None,
            "odometer_adjustment": 0,
            "custom_fields": {},
        }
        for f in v.get("ExtraFields") or []:
            key = VEHICLE_FIELDS.get(re.sub(r"[^a-z]", "", str(f["Name"]).lower()))
            if key and f.get("Value"):
                out[key] = f["Value"]
            elif f.get("Value"):
                out["custom_fields"][f["Name"]] = str(f["Value"])
        loc = str(v.get("ImageLocation") or "")
        pv = PlannedVehicle(
            f"vehicles:{v['_id']}", out, loc.lstrip("/") if loc.startswith("/images/") else None
        )

        def mine(k: str) -> list[Doc]:
            return [r for r in self.cols.get(k, []) if r.get("VehicleId") == v["_id"]]

        jobs: list[tuple[str, Doc, Any, tuple[Any, ...]]] = []
        for coll, cat in WORK.items():
            jobs += [(coll, r, self.work, (coll, cat, r)) for r in mine(coll)]
        jobs += [("gasrecords", r, self.fuel_or_skip, (r, v)) for r in mine("gasrecords")]
        jobs += [("odometerrecords", r, self.odometer, (r,)) for r in mine("odometerrecords")]
        jobs += [("taxrecords", r, self.tax, (r, out.get("plate"))) for r in mine("taxrecords")]
        jobs += [("planrecords", r, self.todo, (r,)) for r in mine("planrecords")]
        jobs += [("notes", r, self.note, (r,)) for r in mine("notes")]
        jobs += [("inspectionrecords", r, self.inspection, (r,)) for r in mine("inspectionrecords")]
        for coll, r, fn, args in jobs:
            if rec := self.guard(coll, r, fn, *args):
                pv.records.append(rec)
        for r in mine("reminderrecords"):
            if rem := self.guard("reminderrecords", r, self.reminder, r):
                pv.reminders.append(rem)
        dropped = [x for x in pv.records if x["date"] is None and x["type"] not in ("todo", "note")]
        for _ in dropped:
            self.skip("records without a date")
        pv.records = [x for x in pv.records if x not in dropped]
        return pv

    def fuel_or_skip(self, r: Doc, v: Doc) -> Doc | None:
        if v.get("IsElectric"):
            self.skip("gasrecords (electric)")
        elif not r.get("Gallons") or r["Gallons"] <= 0:
            self.skip("gasrecords (no volume)")
        else:
            return self.fuel(r)
        return None

    def odometer(self, r: Doc) -> Doc:
        return self.base("odometerrecords", r, "odometer", None, {}, odometer=r.get("Mileage"))

    def work(self, coll: str, cat: str, r: Doc) -> Doc:
        items = [
            {
                "description": f"{h.get('Description') or ''} ({h['PartNumber']})"
                if h.get("PartNumber")
                else h.get("Description"),
                "cost": self.money(h.get("Cost")),
                "quantity": float(h["Quantity"]) if h.get("Quantity") is not None else None,
            }
            for h in r.get("RequisitionHistory") or []
        ]
        return self.base(
            coll, r, "work", r.get("Description"), {"category": cat, "line_items": items}
        )

    def fuel(self, r: Doc) -> Doc:
        d = {
            "volume": float(r["Gallons"]),
            "full_tank": r.get("IsFillToFull", True),
            "missed_previous": bool(r.get("MissedFuelUp")),
        }
        return self.base("gasrecords", r, "fuel", None, d)

    def tax(self, r: Doc, plate: str | None) -> Doc:
        sid = f"taxrecords:{r['_id']}"
        guessed, certain = self.tax_type(r)
        rtype = self.tax_types.get(sid, guessed)
        if not certain and sid not in self.tax_types:
            self.warn(
                "Some tax records have an unclear type (check type); defaulted to registration"
            )
        expiry = None
        d = self.day(r.get("Date"))
        if r.get("IsRecurring") and d:
            n = self.months(
                r, "RecurringInterval", "CustomMonthIntervalUnit", "CustomMonthInterval"
            )
            expiry = add_months(d, n) if n else None
        details: dict[str, Any] = {"expiry_date": expiry}
        if rtype == "registration" and plate:
            details["plate"] = plate
        self.plan.tax_choices.append(
            {
                "source_id": sid,
                "description": r.get("Description"),
                "date": d,
                "guessed_type": rtype,
            }
        )
        return self.base("taxrecords", r, rtype, r.get("Description"), details, odometer=None)

    def todo(self, r: Doc) -> Doc:
        details = {
            "priority": PRIORITY.get(str(r.get("Priority")), "medium"),
            "status": PROGRESS.get(str(r.get("Progress")), "backlog"),
            "quoted": self.money(r.get("Cost")),
        }
        rec = self.base(
            "planrecords", r, "todo", r.get("Description"), details, odometer=None, cost=None
        )
        rec["date"] = self.day(r.get("DateCreated"))
        return rec

    def note(self, r: Doc) -> Doc:
        rec = self.base(
            "notes",
            r,
            "note",
            r.get("Description"),
            {"pinned": bool(r.get("Pinned"))},
            odometer=None,
            cost=None,
        )
        rec["notes"] = r.get("NoteText")
        return rec

    def inspection(self, r: Doc) -> Doc:
        results = r.get("Results") or []
        lines = []
        failed = False
        for x in results:
            vals = x.get("Values") or []
            failed = failed or bool(x.get("Failed")) or any(v.get("IsFail") for v in vals)
            picked = [v.get("Description") for v in vals if v.get("IsSelected")] or [x.get("Notes")]
            lines.append(f"{x.get('Description')}: {', '.join(str(p) for p in picked if p)}")
        rec = self.base(
            "inspectionrecords",
            r,
            "inspection",
            r.get("Description"),
            {"result": "fail" if failed else "pass"},
        )
        rec["notes"] = "\n".join(lines) or None
        return rec

    def reminder(self, r: Doc) -> Doc | None:
        metric = r.get("Metric") or "Date"
        due_date = self.day(r.get("Date")) if metric in ("Date", "Both") else None
        due_km = (r.get("Mileage") or None) if metric in ("Odometer", "Both") else None
        months = km = None
        if r.get("IsRecurring"):
            # LubeLogger fills both intervals; only the one Metric selects is live
            if metric in ("Date", "Both"):
                months = self.months(
                    r, "ReminderMonthInterval", "CustomMonthIntervalUnit", "CustomMonthInterval"
                )
            if metric in ("Odometer", "Both"):
                name = r.get("ReminderMileageInterval")
                km = (
                    r.get("CustomMileageInterval") or None
                    if name == "Other"
                    else mileage_interval(name)
                )
            if not months and not km:
                self.warn("A recurring reminder has no usable interval; imported as one-off")
        if due_date is None and due_km is None:
            self.skip("reminders without a due date or odometer")
            return None
        return {
            "title": r.get("Description") or "Reminder",
            "notes": r.get("Notes"),
            "due_date": due_date,
            "due_km": due_km,
            "repeat_months": months,
            "repeat_km": km,
            "source_id": f"reminderrecords:{r['_id']}",
        }

    def run(self) -> ImportPlan:
        for v in self.cols.get("vehicles", []):
            if pv := self.guard("vehicles", v, self.vehicle, v):
                self.plan.vehicles.append(pv)
        for k in SKIPPED:
            if n := len(self.cols.get(k, [])):
                self.skipped[k] = n
        if not any(
            rem["repeat_months"] or rem["repeat_km"]
            for pv in self.plan.vehicles
            for rem in pv.reminders
        ):
            self.warn("no recurring reminders found")
        return self.plan


def build_plan(collections: dict[str, list[Doc]], user_config: Doc, options: Doc) -> ImportPlan:
    return _Mapper(collections, user_config, options).run()
