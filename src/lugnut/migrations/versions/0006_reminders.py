"""reminders"""

import sqlalchemy as sa
from alembic import op

revision = "0006_reminders"
down_revision = "0005_attachments"


def upgrade() -> None:
    op.create_table(
        "reminder",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "vehicle_id",
            sa.Integer,
            sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("notes", sa.String),
        sa.Column("due_date", sa.Date),
        sa.Column("due_km", sa.Float),
        sa.Column("repeat_months", sa.Integer),
        sa.Column("repeat_km", sa.Float),
        sa.Column("warn_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("warn_km", sa.Float, nullable=False, server_default="1000"),
        sa.Column("kind", sa.String, nullable=False, server_default="manual"),
        sa.Column("expiry_type", sa.String),
        sa.Column("source_record_id", sa.Integer, sa.ForeignKey("record.id", ondelete="SET NULL")),
        sa.Column("notified_state", sa.String),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_reminder_vehicle", "reminder", ["vehicle_id"])
    op.create_index(
        "ux_reminder_expiry",
        "reminder",
        ["vehicle_id", "expiry_type"],
        unique=True,
        sqlite_where=sa.text("kind = 'expiry'"),
    )


def downgrade() -> None:
    op.drop_table("reminder")
