"""Link orphan field-bound components with auto-generated component_key (admin UI).

When `component_key` matches `phone_input_*`, `checkbox_*`, or `date_picker_*` and the row
has no binding / no field_definition_id, assign the canonical binding used on the same
flow step in seeds (phone_number, terms_accepted, date_of_birth) only if that binding is
not already used on the same screen (avoids duplicate keys).

Revision ID: 093
Revises: 092
"""
from alembic import op
from sqlalchemy import text

revision = "093"
down_revision = "092"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    for ctype, key_pattern, binding, fd_slug in (
        ("phone_input", r"^phone_input_[a-z0-9]+$", "phone_number", "phone-number"),
        ("checkbox", r"^checkbox_[a-z0-9]+$", "terms_accepted", "terms-accepted"),
        ("date_picker", r"^date_picker_[a-z0-9]+$", "date_of_birth", "date-of-birth"),
    ):
        conn.execute(
            text(
                """
                UPDATE public.registration_screen_components rsc
                SET
                    binding_slug = :binding,
                    field_definition_id = (
                        SELECT id FROM public.field_definitions
                        WHERE slug = :fd_slug LIMIT 1
                    )
                WHERE rsc.component_type = :ctype
                  AND rsc.component_key ~ :key_pattern
                  AND (rsc.binding_slug IS NULL OR length(trim(rsc.binding_slug)) = 0)
                  AND rsc.field_definition_id IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM public.registration_screen_components x
                      WHERE x.screen_id = rsc.screen_id
                        AND x.binding_slug = :binding
                        AND x.id <> rsc.id
                  )
                """
            ),
            {
                "ctype": ctype,
                "key_pattern": key_pattern,
                "binding": binding,
                "fd_slug": fd_slug,
            },
        )


def downgrade() -> None:
    pass
