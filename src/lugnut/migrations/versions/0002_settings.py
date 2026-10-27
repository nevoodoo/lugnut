"""install settings"""

import sqlalchemy as sa
from alembic import op

revision = "0002_settings"
down_revision = "0001_initial"


def upgrade() -> None:
    op.create_table(
        "setting",
        sa.Column("key", sa.String, primary_key=True),
        sa.Column("value", sa.JSON, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("setting")
