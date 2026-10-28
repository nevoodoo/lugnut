import json
import re
from importlib.resources import files
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from lugnut.auth.deps import DB
from lugnut.auth.routes import Reader, Writer
from lugnut.models import Setting

router = APIRouter(prefix="/api")
KEY = "install"
WEBHOOK_KEY = "discord_webhook_url"
DEFAULT_REGION = "au"


def load_regions() -> dict[str, dict[str, Any]]:
    out = {}
    for f in sorted(files("lugnut").joinpath("regions").iterdir(), key=lambda p: p.name):
        if f.name.endswith(".json"):
            out[f.name.removesuffix(".json")] = json.loads(f.read_text("utf-8"))
    return out


class InstallSettings(BaseModel):
    region: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    distance_unit: Literal["km", "mi"]
    volume_unit: Literal["L", "gal_us", "gal_imp"]
    date_format: str = Field(min_length=1, max_length=32)


class SettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region: str | None = None
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")
    distance_unit: Literal["km", "mi"] | None = None
    volume_unit: Literal["L", "gal_us", "gal_imp"] | None = None
    date_format: str | None = Field(None, min_length=1, max_length=32)
    discord_webhook_set: bool | None = None  # read-only; accepted so a GET body PUTs back


class SettingsOut(InstallSettings):
    discord_webhook_set: bool


class DiscordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str | None = Field(None, max_length=512)


def _bad(field: str, msg: str, value: Any) -> RequestValidationError:
    return RequestValidationError(
        [{"type": "value_error", "loc": ("body", field), "msg": msg, "input": value}]
    )


WEBHOOK_PATH = re.compile(r"/api/webhooks/\d+/[A-Za-z0-9_-]+", re.ASCII)
WEBHOOK_HOSTS = ("discord.com", "discordapp.com", "ptb.discord.com", "canary.discord.com")


def is_discord_webhook(url: str) -> bool:
    """Only Discord webhook URLs, so the server can't be pointed at arbitrary hosts (SSRF)."""
    if any(c.isspace() or not c.isprintable() for c in url):
        return False  # urlsplit would silently strip some of these
    try:
        u = urlsplit(url)
        port = u.port
    except ValueError:
        return False
    return (
        u.scheme == "https"
        and u.hostname in WEBHOOK_HOSTS
        and u.username is None
        and u.password is None
        and port in (None, 443)
        and not u.query
        and not u.fragment
        and WEBHOOK_PATH.fullmatch(u.path) is not None
    )


def get_webhook_url(db: Session) -> str | None:
    row = db.get(Setting, WEBHOOK_KEY)
    return row.value if row else None


def _out(db: Session, install: InstallSettings) -> SettingsOut:
    return SettingsOut(**install.model_dump(), discord_webhook_set=bool(get_webhook_url(db)))


def _defaults(code: str) -> InstallSettings:
    r = load_regions()[code]
    return InstallSettings(region=code, **{k: r[k] for k in list(InstallSettings.model_fields)[1:]})


def get_install_settings(db: Session) -> InstallSettings:
    row = db.get(Setting, KEY)
    return InstallSettings.model_validate(row.value) if row else _defaults(DEFAULT_REGION)


@router.get("/regions")
def list_regions(_: Reader) -> list[dict[str, Any]]:
    return list(load_regions().values())


@router.get("/settings")
def read_settings(_: Reader, db: DB) -> SettingsOut:
    return _out(db, get_install_settings(db))


@router.put("/settings")
def replace_settings(body: SettingsIn, _: Writer, db: DB) -> SettingsOut:
    code = body.region or get_install_settings(db).region
    if code not in load_regions():
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": ("body", "region"),
                    "msg": f"Unknown region {code!r}",
                    "input": code,
                }
            ]
        )
    new = _defaults(code).model_copy(
        update=body.model_dump(exclude_none=True, exclude={"discord_webhook_set"})
    )
    value = new.model_dump()
    row = db.get(Setting, KEY)
    if row:
        row.value = value
    else:
        db.add(Setting(key=KEY, value=value))
    db.commit()
    return _out(db, new)


@router.put("/settings/discord")
def set_discord(body: DiscordIn, _: Writer, db: DB) -> SettingsOut:
    row = db.get(Setting, WEBHOOK_KEY)
    if body.url is None:
        if row:
            db.delete(row)
    else:
        url = body.url
        if not is_discord_webhook(url):
            raise _bad("url", "Must be a https://discord.com/api/webhooks/... URL", "")
        if row:
            row.value = url
        else:
            db.add(Setting(key=WEBHOOK_KEY, value=url))
    db.commit()
    return _out(db, get_install_settings(db))


@router.post("/settings/discord/test")
def test_discord(_: Writer, db: DB) -> dict[str, Any]:
    from lugnut.reminders.notify import NotifyError, discord_send  # avoids an import cycle

    url = get_webhook_url(db)
    if not url:
        return {"ok": False, "error": "No webhook set"}
    try:
        discord_send(url, {"content": "Lugnut test message", "allowed_mentions": {"parse": []}})
    except NotifyError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}
