import datetime as dt
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lugnut.db import Base
from lugnut.vehicles.models import Vehicle


class JobType(Base):
    __tablename__ = "job_type"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    builtin: Mapped[bool] = mapped_column(default=False)


class LineItem(Base):
    __tablename__ = "line_item"
    __table_args__ = (Index("ix_line_item_record", "record_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("record.id", ondelete="CASCADE"))
    position: Mapped[int]
    job_type_id: Mapped[int | None] = mapped_column(ForeignKey("job_type.id", ondelete="SET NULL"))
    description: Mapped[str | None]
    cost: Mapped[int | None]
    quantity: Mapped[float | None]


class Record(Base):
    __tablename__ = "record"
    __table_args__ = (
        Index("ix_record_vehicle_date", "vehicle_id", "date"),
        Index(
            "ux_record_source",
            "source",
            "source_id",
            unique=True,
            sqlite_where=text("source IS NOT NULL"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id", ondelete="CASCADE"))
    type: Mapped[str]
    date: Mapped[dt.date | None]
    odometer_km: Mapped[float | None]
    cost: Mapped[int | None]
    is_estimate: Mapped[bool] = mapped_column(default=False)
    title: Mapped[str | None]
    notes: Mapped[str | None]
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    custom_fields: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source: Mapped[str | None]
    source_id: Mapped[str | None]
    created_at: Mapped[dt.datetime]
    updated_at: Mapped[dt.datetime]

    vehicle: Mapped[Vehicle] = relationship()
    line_items: Mapped[list[LineItem]] = relationship(
        order_by=LineItem.position, cascade="all, delete-orphan", passive_deletes=True
    )
