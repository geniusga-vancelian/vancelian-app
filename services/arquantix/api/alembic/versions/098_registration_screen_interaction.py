"""Registration step screens: form vs interaction (SMS phone verification, etc.).

Revision ID: 098
Revises: 097
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "098"
down_revision = "097"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "registration_step_screens",
        sa.Column("screen_type", sa.Text(), nullable=False, server_default="form"),
        schema="public",
    )
    op.add_column(
        "registration_step_screens",
        sa.Column("interaction_type", sa.Text(), nullable=True),
        schema="public",
    )
    op.add_column(
        "registration_step_screens",
        sa.Column("interaction_config_json", JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("registration_step_screens", "interaction_config_json", schema="public")
    op.drop_column("registration_step_screens", "interaction_type", schema="public")
    op.drop_column("registration_step_screens", "screen_type", schema="public")
