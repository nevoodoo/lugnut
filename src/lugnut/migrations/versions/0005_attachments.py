"""attachments and vehicle photos"""

import sqlalchemy as sa
from alembic import op

revision = "0005_attachments"
down_revision = "0004_records"

PHOTO_FK = "fk_vehicle_photo_attachment"


def upgrade() -> None:
    op.create_table(
        "attachment",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "vehicle_id",
            sa.Integer,
            sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("record_id", sa.Integer, sa.ForeignKey("record.id", ondelete="CASCADE")),
        sa.Column("filename", sa.String, nullable=False),
        sa.Column("content_type", sa.String, nullable=False),
        sa.Column("size", sa.Integer, nullable=False),
        sa.Column("sha256", sa.String, nullable=False),
        sa.Column("stored_name", sa.String, nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_attachment_vehicle", "attachment", ["vehicle_id"])
    op.create_index("ix_attachment_record", "attachment", ["record_id"])
    with op.batch_alter_table("vehicle") as batch:
        batch.create_foreign_key(
            PHOTO_FK, "attachment", ["photo_attachment_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("vehicle") as batch:
        batch.drop_constraint(PHOTO_FK, type_="foreignkey")
    op.drop_table("attachment")
