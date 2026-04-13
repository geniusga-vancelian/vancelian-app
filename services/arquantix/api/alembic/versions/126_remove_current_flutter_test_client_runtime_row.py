"""Supprime la ligne legacy current_flutter_test_client_id de app_runtime_settings.

Le client Flutter « courant » pour le dev est désormais dans
``api/.current_test_client_id`` ou ``ARQUANTIX_TEST_CLIENT_ID``.

Revision ID: 126
Revises: 125
"""
from __future__ import annotations

from alembic import op

revision = "126"
down_revision = "125"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM public.app_runtime_settings WHERE key = 'current_flutter_test_client_id'"
    )


def downgrade() -> None:
    # Pas de réinsertion automatique (UUID inconnu) — utiliser l’admin ou le fichier local.
    pass
