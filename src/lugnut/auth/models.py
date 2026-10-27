from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from lugnut.db import Base


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    created_at: Mapped[datetime]


class ApiToken(Base):
    __tablename__ = "api_token"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    token_hash: Mapped[str] = mapped_column(unique=True)
    scope: Mapped[str]
    created_at: Mapped[datetime]
    last_used_at: Mapped[datetime | None]


class LoginSession(Base):
    __tablename__ = "session"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]
