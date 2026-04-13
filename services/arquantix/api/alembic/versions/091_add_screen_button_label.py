"""Add button_label and button_label_i18n to registration_step_screens.

Revision ID: 091
Revises: 090
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "091"
down_revision = "090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "registration_step_screens",
        sa.Column("button_label", sa.String(), nullable=True),
        schema="public",
    )
    op.add_column(
        "registration_step_screens",
        sa.Column("button_label_i18n", JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("registration_step_screens", "button_label_i18n", schema="public")
    op.drop_column("registration_step_screens", "button_label", schema="public")
