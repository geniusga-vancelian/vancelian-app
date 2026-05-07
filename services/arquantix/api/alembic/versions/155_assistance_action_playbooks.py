"""Catalogue déclaratif CAL — ``assistance_action_playbooks``.

Playbooks versionnés en base (étapes, tools, consignes LLM) ; éditables
depuis l'admin web. Injection dans le prompt de l'agent ``product``.
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "155"
down_revision = "154"
branch_labels = None
depends_on = None

_DEF_CRYPTO = {
    "target_kinds": ["crypto_buy"],
    "steps": [
        {
            "id": "list_sources",
            "tool": "show_invest_source_accounts",
            "order": 1,
            "instruction_fr": (
                "Dès que le client veut acheter de la crypto et le symbole "
                "(ex. BTC) est connu, appelle `show_invest_source_accounts` avec "
                "`target_kind=crypto_buy` et `target_id=SYMBOLE` pour afficher "
                "la liste des comptes sources cliquables (ne pas renvoyer vers "
                "« Mes informations » générique)."
            ),
        },
        {
            "id": "confirmation",
            "tool": "show_invest_confirmation_draft",
            "order": 2,
            "instruction_fr": (
                "Quand le montant et le compte source (clé `account_key` issue "
                "de la liste) sont disponibles, appelle "
                "`show_invest_confirmation_draft` pour l'encart de confirmation "
                "natif (deep-link avec montant)."
            ),
        },
    ],
    "required_slots_fr": "Symbole crypto, montant, devise du montant, compte source.",
    "unavailable_message_fr": (
        "L'achat spot guidé depuis le chat n'est pas disponible pour cet actif."
    ),
}

_DEF_BUNDLE = {
    "target_kinds": ["bundle"],
    "steps": [
        {
            "id": "list_sources",
            "tool": "show_invest_source_accounts",
            "order": 1,
            "instruction_fr": (
                "Quand le bundle crypto (UUID produit) est identifié, appelle "
                "`show_invest_source_accounts` avec `target_kind=bundle` et "
                "`target_id` = UUID du bundle."
            ),
        },
        {
            "id": "confirmation",
            "tool": "show_invest_confirmation_draft",
            "order": 2,
            "instruction_fr": (
                "Avec montant + `account_key`, appelle `show_invest_confirmation_draft` "
                "(`target_kind=bundle`)."
            ),
        },
    ],
    "required_slots_fr": "UUID bundle, montant, devise, compte source.",
    "unavailable_message_fr": (
        "L'investissement bundle guidé depuis le chat est indisponible pour ce produit."
    ),
}


def upgrade() -> None:
    op.create_table(
        "assistance_action_playbooks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("action_key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("transaction_kind", sa.String(length=32), nullable=False),
        sa.Column(
            "agent_id",
            sa.String(length=32),
            nullable=False,
            server_default="product",
        ),
        sa.Column(
            "definition",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        schema="public",
    )
    op.create_index(
        "ix_assistance_action_playbooks_enabled_sort",
        "assistance_action_playbooks",
        ["is_enabled", "sort_order"],
        schema="public",
    )
    op.create_index(
        "uq_assistance_action_playbooks_action_key",
        "assistance_action_playbooks",
        ["action_key"],
        unique=True,
        schema="public",
    )

    bind = op.get_bind()
    rows = [
        {
            "action_key": "crypto_buy",
            "label": "Achat crypto spot (CAL)",
            "description": "Parcours guidé : comptes sources puis confirmation native.",
            "transaction_kind": "crypto_buy",
            "agent_id": "product",
            "definition": json.dumps(_DEF_CRYPTO),
            "is_enabled": True,
            "sort_order": 10,
        },
        {
            "action_key": "bundle_invest",
            "label": "Investir dans un bundle crypto (CAL)",
            "description": "Parcours guidé bundle : sources puis confirmation.",
            "transaction_kind": "bundle_invest",
            "agent_id": "product",
            "definition": json.dumps(_DEF_BUNDLE),
            "is_enabled": True,
            "sort_order": 20,
        },
    ]
    for r in rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO public.assistance_action_playbooks
                (action_key, label, description, transaction_kind, agent_id, definition, is_enabled, sort_order)
                VALUES (:action_key, :label, :description, :transaction_kind, :agent_id, CAST(:definition AS jsonb), :is_enabled, :sort_order)
                """
            ),
            r,
        )


def downgrade() -> None:
    op.drop_index(
        "uq_assistance_action_playbooks_action_key",
        table_name="assistance_action_playbooks",
        schema="public",
    )
    op.drop_index(
        "ix_assistance_action_playbooks_enabled_sort",
        table_name="assistance_action_playbooks",
        schema="public",
    )
    op.drop_table("assistance_action_playbooks", schema="public")
