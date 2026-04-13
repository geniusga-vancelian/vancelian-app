"""Registration runtime settings — current jurisdiction selector."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = "089"
down_revision = "088"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registration_runtime_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("current_jurisdiction_code", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )

    conn = op.get_bind()
    setting_id = str(uuid.uuid4())
    conn.execute(text(
        "INSERT INTO public.registration_runtime_settings (id, current_jurisdiction_code) "
        "VALUES (:id, :code)"
    ), {"id": setting_id, "code": "EU"})


def downgrade() -> None:
    op.drop_table("registration_runtime_settings", schema="public")
