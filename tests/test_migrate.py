import os
import sqlite3

import pytest
from alembic import command
from alembic.script import ScriptDirectory

import lugnut.migrate as migrate
from lugnut.migrate import DataDirError, MigrationFailed, _alembic_config, upgrade_database
from lugnut.settings import Settings


def downgrade_one_for_test(settings: Settings) -> None:
    command.downgrade(_alembic_config(settings), "-1")


def _revision(db) -> str | None:
    con = sqlite3.connect(db)
    try:
        row = con.execute("select version_num from alembic_version").fetchone()
        return row[0] if row else None
    finally:
        con.close()


def test_backup_taken_before_migrating(tmp_path):
    # catches: migrating without a safety copy
    s = Settings(data_dir=tmp_path)
    upgrade_database(s)  # fresh db goes to head, no backup needed
    downgrade_one_for_test(s)
    backup = upgrade_database(s)
    assert backup and backup.parent == tmp_path / "backups"
    # the backup holds the pre-upgrade schema, the live db is at head
    head = ScriptDirectory.from_config(_alembic_config(s)).get_current_head()
    assert _revision(backup) != head
    assert _revision(s.db_path) == head


def test_failed_migration_leaves_backup_and_raises(tmp_path, monkeypatch):
    # catches: app starting on a half-migrated db
    s = Settings(data_dir=tmp_path)
    upgrade_database(s)
    downgrade_one_for_test(s)

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(migrate.command, "upgrade", boom)
    with pytest.raises(MigrationFailed) as e:
        upgrade_database(s)
    assert str(tmp_path / "backups") in str(e.value)
    assert list((tmp_path / "backups").glob("*.db"))


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_unwritable_data_dir_fails_clearly(tmp_path):
    # catches: opaque sqlite errors on bad volume mounts
    tmp_path.chmod(0o500)
    try:
        with pytest.raises(DataDirError, match=str(tmp_path)):
            upgrade_database(Settings(data_dir=tmp_path / "sub"))
    finally:
        tmp_path.chmod(0o700)
