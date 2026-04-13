"""Presentation decks, versions, slide templates, version slides (hybrid persistence).

Revision ID: 095
Revises: 094
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "095"
down_revision = "094"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presentation_slide_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False, server_default="general"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("preview_image_url", sa.Text(), nullable=True),
        sa.Column("schema_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("default_content_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("design_tokens_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("key", name="uq_presentation_slide_template_key"),
        schema="public",
    )

    op.create_table(
        "presentation_decks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deck_type", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_presentation_deck_slug"),
        schema="public",
    )

    op.create_table(
        "presentation_deck_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("presentation_id", UUID(as_uuid=True), sa.ForeignKey("public.presentation_decks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("version_label", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("snapshot_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("presentation_id", "version_number", name="uq_presentation_deck_version_num"),
        schema="public",
    )

    op.create_index(
        "uq_presentation_deck_one_current",
        "presentation_deck_versions",
        ["presentation_id"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("is_current = true"),
    )

    op.add_column(
        "presentation_decks",
        sa.Column(
            "current_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.presentation_deck_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        schema="public",
    )

    op.create_table(
        "presentation_version_slides",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "presentation_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.presentation_deck_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "slide_template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.presentation_slide_templates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("slide_title", sa.Text(), nullable=True),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("content_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("style_overrides_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_presentation_version_slides_version_id",
        "presentation_version_slides",
        ["presentation_version_id"],
        schema="public",
    )

    # Seed demo templates (keys alignés avec la galerie front quand possible)
    op.execute(
        sa.text(
            """
            INSERT INTO public.presentation_slide_templates
            (key, name, category, description, status, schema_json, default_content_json)
            VALUES
            (
              'title',
              'Title slide',
              'cover',
              'Couverture titre / sous-titre',
              'active',
              '{"type":"object","properties":{"title":{"type":"string"},"subtitle":{"type":"string"},"badge":{"type":"string"}}}'::jsonb,
              '{"title":"Nouvelle présentation","subtitle":"","badge":""}'::jsonb
            ),
            (
              'section-divider',
              'Section divider',
              'structure',
              'Séparation de section',
              'active',
              '{"type":"object","properties":{"sectionTitle":{"type":"string"},"kicker":{"type":"string"}}}'::jsonb,
              '{"sectionTitle":"Section","kicker":""}'::jsonb
            ),
            (
              'metrics',
              'KPI / Metrics',
              'data',
              'Grille de métriques',
              'active',
              '{"type":"object","properties":{"metrics":{"type":"array","items":{"type":"object"}}}}'::jsonb,
              '{"metrics":[{"label":"KPI 1","value":"—"},{"label":"KPI 2","value":"—"}]}'::jsonb
            ),
            (
              'two-column',
              'Two columns',
              'content',
              'Texte + visuel',
              'active',
              '{"type":"object","properties":{"leftTitle":{"type":"string"},"leftBody":{"type":"string"},"rightCaption":{"type":"string"}}}'::jsonb,
              '{"leftTitle":"Titre","leftBody":"Corps","rightCaption":""}'::jsonb
            ),
            (
              'team',
              'Team',
              'people',
              'Membres',
              'active',
              '{"type":"object","properties":{"members":{"type":"array","items":{"type":"object"}}}}'::jsonb,
              '{"members":[{"name":"Nom","role":"Rôle","bio":"Bio courte"}]}'::jsonb
            ),
            (
              'quote',
              'Quote',
              'content',
              'Citation',
              'active',
              '{"type":"object","properties":{"quote":{"type":"string"},"author":{"type":"string"},"role":{"type":"string"}}}'::jsonb,
              '{"quote":"","author":"","role":""}'::jsonb
            ),
            (
              'closing',
              'Closing',
              'cover',
              'Slide de fin',
              'active',
              '{"type":"object","properties":{"headline":{"type":"string"},"cta":{"type":"string"}}}'::jsonb,
              '{"headline":"Merci","cta":"contact@vancelian.com"}'::jsonb
            );
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_presentation_version_slides_version_id", table_name="presentation_version_slides", schema="public")
    op.drop_table("presentation_version_slides", schema="public")
    op.drop_column("presentation_decks", "current_version_id", schema="public")
    op.drop_index("uq_presentation_deck_one_current", table_name="presentation_deck_versions", schema="public")
    op.drop_table("presentation_deck_versions", schema="public")
    op.drop_table("presentation_decks", schema="public")
    op.drop_table("presentation_slide_templates", schema="public")
