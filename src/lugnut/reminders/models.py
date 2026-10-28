import datetime as dt

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from lugnut.db import Base


class Reminder(Base):
    __tablename__ = "reminder"
    __table_args__ = (
        Index(
            "ux_reminder_expiry",
            "vehicle_id",
            "expiry_type",
            unique=True,
            sqlite_where=text("kind = 'expiry'"),
        ),
        Index(
            "ux_reminder_source",
            "source",
            "source_id",
            unique=True,
            sqlite_where=text("source IS NOT NULL"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id", ondelete="CASCADE"))
    title: Mapped[str]
    notes: Mapped[str | None]
    due_date: Mapped[dt.date | None]
    due_km: Mapped[float | None]
    repeat_months: Mapped[int | None]
    repeat_km: Mapped[float | None]
    warn_days: Mapped[int] = mapped_column(default=30)
    warn_km: Mapped[float] = mapped_column(default=1000)
    kind: Mapped[str] = mapped_column(default="manual")
    expiry_type: Mapped[str | None]
    source_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("record.id", ondelete="SET NULL")
    )
    source: Mapped[str | None]
    source_id: Mapped[str | None]
    notified_state: Mapped[str | None]
    completed_at: Mapped[dt.datetime | None]
    created_at: Mapped[dt.datetime]
