from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, PlainSerializer


def utcnow() -> datetime:
    return datetime.now(UTC)


def _as_utc(v: datetime) -> datetime:
    return v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)


# Columns hold naive UTC (as 0001 created them); this re-tags on read and writes "Z" out.
UtcDatetime = Annotated[
    datetime,
    AfterValidator(_as_utc),
    PlainSerializer(lambda v: _as_utc(v).isoformat().replace("+00:00", "Z"), return_type=str),
]
