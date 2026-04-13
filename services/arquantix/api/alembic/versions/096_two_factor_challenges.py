"""Two-factor challenges (SMS / email OTP + TOTP audit).

Revision ID: 096
Revises: 095
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "096"
down_revision = "095"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "two_factor_challenges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("public.persons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_two_factor_challenges_person_id", "two_factor_challenges", ["person_id"], schema="public")
    op.create_index("ix_two_factor_challenges_status", "two_factor_challenges", ["status"], schema="public")
    op.create_index("ix_two_factor_challenges_expires_at", "two_factor_challenges", ["expires_at"], schema="public")
    op.create_index(
        "ix_two_factor_challenges_person_created",
        "two_factor_challenges",
        ["person_id", "created_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_two_factor_challenges_person_created", table_name="two_factor_challenges", schema="public")
    op.drop_index("ix_two_factor_challenges_expires_at", table_name="two_factor_challenges", schema="public")
    op.drop_index("ix_two_factor_challenges_status", table_name="two_factor_challenges", schema="public")
    op.drop_index("ix_two_factor_challenges_person_id", table_name="two_factor_challenges", schema="public")
    op.drop_table("two_factor_challenges", schema="public")
