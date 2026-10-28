import datetime as dt

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from lugnut.db import Base


class Attachment(Base):
    __tablename__ = "attachment"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id", ondelete="CASCADE"))
    record_id: Mapped[int | None] = mapped_column(ForeignKey("record.id", ondelete="CASCADE"))
    filename: Mapped[str]  # display only, never used for paths
    content_type: Mapped[str]
    size: Mapped[int]
    sha256: Mapped[str]
    stored_name: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[dt.datetime]
