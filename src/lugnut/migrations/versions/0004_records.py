"""records, line items and job types"""

import sqlalchemy as sa
from alembic import op

revision = "0004_records"
down_revision = "0003_vehicles"

BUILTIN_JOB_TYPES = [
    "Oil and filter",
    "Air filter",
    "Cabin filter",
    "Spark plugs",
    "Brake pads",
    "Brake rotors",
    "Brake fluid",
    "Coolant",
    "Transmission fluid",
    "Tyres",
    "Wheel alignment",
    "Battery",
    "Wipers",
    "Timing belt",
    "Drive belt",
    "Suspension",
    "Diagnostics",
    "Other",
]


def upgrade() -> None:
    job_type = op.create_table(
        "job_type",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True),
        sa.Column("builtin", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.bulk_insert(job_type, [{"name": n, "builtin": True} for n in BUILTIN_JOB_TYPES])

    op.create_table(
        "record",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "vehicle_id",
            sa.Integer,
            sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("date", sa.Date),
        sa.Column("odometer_km", sa.Float),
        sa.Column("cost", sa.Integer),
        sa.Column("is_estimate", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("title", sa.String),
        sa.Column("notes", sa.String),
        sa.Column("tags", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("custom_fields", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("details", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("source", sa.String),
        sa.Column("source_id", sa.String),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_record_vehicle_date", "record", ["vehicle_id", "date"])
    op.create_index(
        "ux_record_source",
        "record",
        ["source", "source_id"],
        unique=True,
        sqlite_where=sa.text("source IS NOT NULL"),
    )

    op.create_table(
        "line_item",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "record_id",
            sa.Integer,
            sa.ForeignKey("record.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("job_type_id", sa.Integer, sa.ForeignKey("job_type.id", ondelete="SET NULL")),
        sa.Column("description", sa.String),
        sa.Column("cost", sa.Integer),
        sa.Column("quantity", sa.Float),
    )
    op.create_index("ix_line_item_record", "line_item", ["record_id"])


def downgrade() -> None:
    op.drop_table("line_item")
    op.drop_table("record")
    op.drop_table("job_type")
