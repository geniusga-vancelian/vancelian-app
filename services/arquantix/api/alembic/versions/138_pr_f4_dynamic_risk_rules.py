"""PR F.4 — règles de risque dynamiques (auth_risk_rules).

Revision ID: 138
Revises: 137
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "138"
down_revision = "137"
branch_labels = None
depends_on = None

# Jeux de règles alignés sur les combinaisons PR F.2 historiques (exemples seed).
R1 = uuid.UUID("f4f40001-0000-4000-8000-000000000001")
R2 = uuid.UUID("f4f40002-0000-4000-8000-000000000002")
R3 = uuid.UUID("f4f40003-0000-4000-8000-000000000003")
R4 = uuid.UUID("f4f40004-0000-4000-8000-000000000004")


def upgrade() -> None:
    op.create_table(
        "auth_risk_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column(
            "conditions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_auth_risk_rules_priority",
        "auth_risk_rules",
        ["priority"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_auth_risk_rules_enabled",
        "auth_risk_rules",
        ["enabled"],
        unique=False,
        schema="public",
    )

    rules = sa.table(
        "auth_risk_rules",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("priority", sa.Integer),
        sa.column("conditions", postgresql.JSONB),
        sa.column("action", sa.String),
        sa.column("enabled", sa.Boolean),
        schema="public",
    )
    op.bulk_insert(
        rules,
        [
            {
                "id": R1,
                "name": "new_device_and_country_change",
                "priority": 10,
                "conditions": {"all": ["new_device", "country_changed"]},
                "action": "BLOCK",
                "enabled": True,
            },
            {
                "id": R2,
                "name": "ip_change_and_attestation_low",
                "priority": 20,
                "conditions": {"all": ["ip_changed", "attestation_low"]},
                "action": "BLOCK",
                "enabled": True,
            },
            {
                "id": R3,
                "name": "device_churn_and_velocity",
                "priority": 30,
                "conditions": {"all": ["device_churn_and_velocity"]},
                "action": "BLOCK",
                "enabled": True,
            },
            {
                "id": R4,
                "name": "new_device_and_high_velocity",
                "priority": 40,
                "conditions": {"all": ["new_device", "high_velocity"]},
                "action": "STEP_UP",
                "enabled": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_auth_risk_rules_enabled", table_name="auth_risk_rules", schema="public")
    op.drop_index("ix_auth_risk_rules_priority", table_name="auth_risk_rules", schema="public")
    op.drop_table("auth_risk_rules", schema="public")
