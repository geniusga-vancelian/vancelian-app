"""Field definitions engine — enrich field_definitions and link to registration components."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

revision = "088"
down_revision = "087"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 1. Add columns to field_definitions ---
    op.add_column("field_definitions", sa.Column("ui_label", sa.Text(), nullable=True), schema="public")
    op.add_column("field_definitions", sa.Column("component_type_default", sa.Text(), nullable=True), schema="public")
    op.add_column("field_definitions", sa.Column("required_default", sa.Boolean(), nullable=True), schema="public")
    op.add_column("field_definitions", sa.Column("options_json", JSONB(astext_type=sa.Text()), nullable=True), schema="public")

    # --- 2. Add field_definition_id FK to registration_screen_components ---
    op.add_column(
        "registration_screen_components",
        sa.Column("field_definition_id", UUID(as_uuid=True), nullable=True),
        schema="public",
    )
    op.create_foreign_key(
        "fk_reg_component_field_def",
        "registration_screen_components",
        "field_definitions",
        ["field_definition_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
    )

    # --- 3. Backfill ---
    conn = op.get_bind()

    # 3a. Backfill ui_label from field_name_en
    conn.execute(text("""
        UPDATE public.field_definitions
        SET ui_label = field_name_en
        WHERE ui_label IS NULL
    """))

    # 3b. Backfill component_type_default from most common component_type in components
    conn.execute(text("""
        UPDATE public.field_definitions fd
        SET component_type_default = sub.component_type
        FROM (
            SELECT DISTINCT ON (replace(rsc.binding_slug, '_', '-'))
                replace(rsc.binding_slug, '_', '-') AS norm_slug,
                rsc.component_type,
                count(*) AS cnt
            FROM public.registration_screen_components rsc
            WHERE rsc.binding_slug IS NOT NULL
            GROUP BY replace(rsc.binding_slug, '_', '-'), rsc.component_type
            ORDER BY replace(rsc.binding_slug, '_', '-'), cnt DESC
        ) sub
        WHERE fd.slug = sub.norm_slug
          AND fd.component_type_default IS NULL
    """))

    # 3c. Link registration_screen_components to field_definitions via slug normalization
    conn.execute(text("""
        UPDATE public.registration_screen_components rsc
        SET field_definition_id = fd.id
        FROM public.field_definitions fd
        WHERE rsc.binding_slug IS NOT NULL
          AND rsc.field_definition_id IS NULL
          AND replace(rsc.binding_slug, '_', '-') = fd.slug
    """))


def downgrade() -> None:
    op.drop_constraint("fk_reg_component_field_def", "registration_screen_components", schema="public", type_="foreignkey")
    op.drop_column("registration_screen_components", "field_definition_id", schema="public")
    op.drop_column("field_definitions", "options_json", schema="public")
    op.drop_column("field_definitions", "required_default", schema="public")
    op.drop_column("field_definitions", "component_type_default", schema="public")
    op.drop_column("field_definitions", "ui_label", schema="public")
