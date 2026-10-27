import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from lugnut.db import get_engine
from lugnut.settings import Settings


class DataDirError(Exception):
    pass


class MigrationFailed(Exception):
    pass


def _alembic_config(settings: Settings) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{settings.db_path}".replace("%", "%%"))
    return cfg


def _prepare_data_dir(settings: Settings) -> None:
    try:
        settings.backup_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise DataDirError(f"Data directory {settings.data_dir} is not usable: {e}") from e
    if not os.access(settings.data_dir, os.W_OK):
        raise DataDirError(f"Data directory {settings.data_dir} is not writable")


def _backup(settings: Settings, revision: str | None) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dest = settings.backup_dir / f"lugnut-{stamp}-{revision or 'base'}.db"
    src = sqlite3.connect(settings.db_path)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return dest


def upgrade_database(settings: Settings) -> Path | None:
    """Migrate to head. Returns the backup path if a backup was taken."""
    _prepare_data_dir(settings)
    cfg = _alembic_config(settings)
    head = ScriptDirectory.from_config(cfg).get_current_head()
    existed = settings.db_path.exists()
    engine = get_engine(settings)
    try:
        with engine.connect() as conn:
            current = MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()
    if current == head:
        return None
    backup = _backup(settings, current) if existed else None
    try:
        command.upgrade(cfg, "head")
    except Exception as e:
        where = f"backup at {backup}" if backup else "no backup (new database)"
        raise MigrationFailed(f"Migration failed; {where}: {e}") from e
    return backup
