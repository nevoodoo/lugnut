"""import sources on vehicles and reminders; source ids unique per vehicle"""

import sqlalchemy as sa
from alembic import op

revision = "0007_import_sources"
down_revision = "0006_reminders"
WHERE = sa.text("source IS NOT NULL")


def upgrade() -> None:
    for t in ("vehicle", "reminder"):
        op.add_column(t, sa.Column("source", sa.String))
        op.add_column(t, sa.Column("source_id", sa.String))
    # ids restart in every source install, so the same source_id can belong to several vehicles
    op.create_index("ix_vehicle_source", "vehicle", ["source", "source_id"], sqlite_where=WHERE)
    op.create_index(
        "ux_reminder_source",
        "reminder",
        ["vehicle_id", "source", "source_id"],
        unique=True,
        sqlite_where=WHERE,
    )
    op.drop_index("ux_record_source", "record")
    op.create_index(
        "ux_record_source",
        "record",
        ["vehicle_id", "source", "source_id"],
        unique=True,
        sqlite_where=WHERE,
    )


def downgrade() -> None:
    op.drop_index("ux_record_source", "record")
    op.create_index(
        "ux_record_source", "record", ["source", "source_id"], unique=True, sqlite_where=WHERE
    )
    op.drop_index("ux_reminder_source", "reminder")
    op.drop_index("ix_vehicle_source", "vehicle")
    for t in ("vehicle", "reminder"):
        op.drop_column(t, "source_id")
        op.drop_column(t, "source")
