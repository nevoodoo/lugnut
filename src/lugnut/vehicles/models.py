from datetime import date, datetime

from sqlalchemy import JSON, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from lugnut.db import Base


class Vehicle(Base):
    __tablename__ = "vehicle"
    __table_args__ = (
        Index(
            "ux_vehicle_source",
            "source",
            "source_id",
            unique=True,
            sqlite_where=text("source IS NOT NULL"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    year: Mapped[int | None]
    make: Mapped[str | None]
    model: Mapped[str | None]
    plate: Mapped[str | None]
    vin: Mapped[str | None]
    engine_number: Mapped[str | None]
    colour: Mapped[str | None]
    fuel_type: Mapped[str | None]
    distance_unit: Mapped[str | None]
    purchase_date: Mapped[date | None]
    purchase_price: Mapped[int | None]
    sold_date: Mapped[date | None]
    sold_price: Mapped[int | None]
    odometer_adjustment_km: Mapped[float] = mapped_column(default=0)
    # use_alter: vehicle and attachment reference each other
    photo_attachment_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "attachment.id", ondelete="SET NULL", use_alter=True, name="fk_vehicle_photo_attachment"
        )
    )
    custom_fields: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    source: Mapped[str | None]
    source_id: Mapped[str | None]
    archived: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime]
