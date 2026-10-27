from collections.abc import Iterator
from typing import Any

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from lugnut.settings import Settings


def _sqlite_pragmas(dbapi_conn: Any, _record: Any) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


def get_engine(settings: Settings) -> Engine:
    engine = create_engine(f"sqlite:///{settings.db_path}")
    event.listen(engine, "connect", _sqlite_pragmas)
    return engine


def get_session(request: Request) -> Iterator[Session]:
    """FastAPI dependency."""
    with Session(request.app.state.engine) as session:
        yield session
