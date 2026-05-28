"""Phase 5C — consommation unique des raw_onchain_events par correction appliquée."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "164"
down_revision = "163"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "raw_onchain_events",
        sa.Column(
            "consumed_by_correction_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema="public",
    )
    op.create_foreign_key(
        "fk_raw_onchain_events_consumed_by_correction",
        "raw_onchain_events",
        "reconciliation_corrections",
        ["consumed_by_correction_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_raw_onchain_events_consumed_by_correction_id",
        "raw_onchain_events",
        ["consumed_by_correction_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_raw_onchain_events_consumed_by_correction_id",
        table_name="raw_onchain_events",
        schema="public",
    )
    op.drop_constraint(
        "fk_raw_onchain_events_consumed_by_correction",
        "raw_onchain_events",
        schema="public",
        type_="foreignkey",
    )
    op.drop_column("raw_onchain_events", "consumed_by_correction_id", schema="public")
