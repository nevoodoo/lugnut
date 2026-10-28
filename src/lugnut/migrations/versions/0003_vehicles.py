"""vehicles"""

import sqlalchemy as sa
from alembic import op

revision = "0003_vehicles"
down_revision = "0002_settings"


def upgrade() -> None:
    op.create_table(
        "vehicle",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("year", sa.Integer),
        sa.Column("make", sa.String),
        sa.Column("model", sa.String),
        sa.Column("plate", sa.String),
        sa.Column("vin", sa.String),
        sa.Column("engine_number", sa.String),
        sa.Column("colour", sa.String),
        sa.Column("fuel_type", sa.String),
        sa.Column("distance_unit", sa.String),
        sa.Column("purchase_date", sa.Date),
        sa.Column("purchase_price", sa.Integer),
        sa.Column("sold_date", sa.Date),
        sa.Column("sold_price", sa.Integer),
        sa.Column("odometer_adjustment_km", sa.Float, nullable=False, server_default="0"),
        sa.Column("photo_attachment_id", sa.Integer),
        sa.Column("custom_fields", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("archived", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("vehicle")
