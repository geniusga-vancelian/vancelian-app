"""admin_users.person_id — lien 1:1 optionnel vers persons (inscription mobile).

Revision ID: 120
Revises: 119
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "120"
down_revision = "119"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admin_users",
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="public",
    )
    op.create_foreign_key(
        "fk_admin_users_person_id_persons",
        "admin_users",
        "persons",
        ["person_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_admin_users_person_id",
        "admin_users",
        ["person_id"],
        unique=True,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_admin_users_person_id", table_name="admin_users", schema="public")
    op.drop_constraint(
        "fk_admin_users_person_id_persons",
        "admin_users",
        schema="public",
        type_="foreignkey",
    )
    op.drop_column("admin_users", "person_id", schema="public")
