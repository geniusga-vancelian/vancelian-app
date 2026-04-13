"""Add i18n JSONB columns to registration tables.

Adds:
- registration_flow_steps: title_i18n, description_i18n
- registration_step_screens: title_i18n, subtitle_i18n
- registration_jurisdictions: supported_languages

Revision ID: 090
Revises: 089
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "090"
down_revision = "089"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "registration_flow_steps",
        sa.Column("title_i18n", JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )
    op.add_column(
        "registration_flow_steps",
        sa.Column("description_i18n", JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )

    op.add_column(
        "registration_step_screens",
        sa.Column("title_i18n", JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )
    op.add_column(
        "registration_step_screens",
        sa.Column("subtitle_i18n", JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )

    op.add_column(
        "registration_jurisdictions",
        sa.Column("supported_languages", JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("registration_jurisdictions", "supported_languages", schema="public")
    op.drop_column("registration_step_screens", "subtitle_i18n", schema="public")
    op.drop_column("registration_step_screens", "title_i18n", schema="public")
    op.drop_column("registration_flow_steps", "description_i18n", schema="public")
    op.drop_column("registration_flow_steps", "title_i18n", schema="public")
