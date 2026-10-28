"""import sources on vehicles and reminders"""

import sqlalchemy as sa
from alembic import op

revision = "0007_import_sources"
down_revision = "0006_reminders"
TABLES = ("vehicle", "reminder")


def upgrade() -> None:
    for t in TABLES:
        op.add_column(t, sa.Column("source", sa.String))
        op.add_column(t, sa.Column("source_id", sa.String))
        op.create_index(
            f"ux_{t}_source",
            t,
            ["source", "source_id"],
            unique=True,
            sqlite_where=sa.text("source IS NOT NULL"),
        )


def downgrade() -> None:
    for t in TABLES:
        op.drop_index(f"ux_{t}_source", t)
        op.drop_column(t, "source_id")
        op.drop_column(t, "source")
