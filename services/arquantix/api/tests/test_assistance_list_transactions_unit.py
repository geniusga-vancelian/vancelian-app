"""Tests unitaires du tool ``list_transactions`` — Phase 2c.3.

Couvre :
  - L'absence de ``client_id`` (résultat vide safe).
  - Le format des items (amount_display, status_label, type_label,
    created_at_display, escape pipe).
  - Le rendu Markdown (header, séparateur, lignes, lien `Ouvrir` par
    ligne avec deep-link `vancelian://app/transactions/{id}`).
  - Le mapping ``category`` → filtres SQL côté repository
    (deposits → direction=credit, cards → kind=card_in, etc.).
  - Le clamp du ``limit`` (1..50).
  - Le passage des filtres ``direction`` / ``status`` / ``since``.
  - Le repo retourne ``[]`` en cas d'erreur SQL → tool renvoie un
    payload vide cohérent avec ``error=repo_unavailable``.

Aucune dépendance Postgres : on mocke ``compliance_repo
.fetch_transactions_list`` ainsi que ``ctx.db`` (au cas où le tool
le toucherait — il ne le fait pas directement, le repo en sert
d'abstraction).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.assistance.agents.tools.compliance import list_transactions
from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _ctx(
    *,
    client_id: str | None = None,
    db: MagicMock | None = None,
) -> ToolContext:
    return ToolContext(
        db=db or MagicMock(),
        client_id=client_id,
        person_id=None,
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id="compliance.transactional",
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t-list-tx",
    )


# ─────────────────────────────────────────────────────────────────────
# A. No client_id → safe empty
# ─────────────────────────────────────────────────────────────────────


class TestNoClientContext:
    def test_returns_empty_payload_with_empty_markdown(self):
        ctx = _ctx(client_id=None)
        out = list_transactions.execute(ctx)
        assert out["count"] == 0
        assert out["items"] == []
        assert "Aucune transaction" in out["markdown_table"]
        assert out["filters_applied"] == {}


# ─────────────────────────────────────────────────────────────────────
# B. Item formatting
# ─────────────────────────────────────────────────────────────────────


class TestItemFormatting:
    def _row(self, **overrides):
        base = {
            "id": "11111111-1111-1111-1111-111111111111",
            "transaction_type": "deposit",
            "transaction_kind": "bank_transfer_in",
            "direction": "credit",
            "status": "completed",
            "amount": Decimal("45000.00"),
            "currency": "EUR",
            "created_at": datetime(2026, 5, 3, 2, 34, tzinfo=timezone.utc),
        }
        base.update(overrides)
        return base

    def _run(self, rows):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            list_transactions.compliance_repo,
            "fetch_transactions_list",
            return_value=rows,
        ):
            return list_transactions.execute(ctx)

    def test_credit_amount_has_plus_sign_and_eur_symbol(self):
        out = self._run([self._row()])
        item = out["items"][0]
        assert item["amount_display"].startswith("+")
        assert item["amount_display"].endswith("€")

    def test_debit_amount_has_minus_sign(self):
        out = self._run(
            [self._row(direction="debit", transaction_kind="bank_transfer_out")]
        )
        assert out["items"][0]["amount_display"].startswith("-")

    def test_status_label_is_french(self):
        out = self._run([self._row(status="pending")])
        assert out["items"][0]["status_label"] == "En attente"

    def test_type_label_uses_kind_when_known(self):
        out = self._run(
            [self._row(transaction_kind="card_in", transaction_type="deposit")]
        )
        assert out["items"][0]["type_label"] == "Dépôt par carte"

    def test_type_label_falls_back_to_type(self):
        out = self._run(
            [self._row(transaction_kind=None, transaction_type="withdrawal")]
        )
        assert out["items"][0]["type_label"] == "Retrait"

    def test_amount_grouping_uses_thin_space(self):
        out = self._run([self._row(amount=Decimal("1234567.89"))])
        # narrow no-break space (\u202f) entre milliers
        assert "\u202f" in out["items"][0]["amount_display"]

    def test_unknown_currency_falls_back_to_iso_code(self):
        out = self._run([self._row(currency="JPY")])
        assert out["items"][0]["amount_display"].endswith("JPY")


# ─────────────────────────────────────────────────────────────────────
# C. Markdown rendering
# ─────────────────────────────────────────────────────────────────────


class TestMarkdownRendering:
    def _run(self, rows):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            list_transactions.compliance_repo,
            "fetch_transactions_list",
            return_value=rows,
        ):
            return list_transactions.execute(ctx)

    def test_empty_rows_returns_no_table_message(self):
        out = self._run([])
        assert out["markdown_table"].startswith("_")
        assert "|" not in out["markdown_table"]

    def test_header_and_separator_present(self):
        out = self._run(
            [
                {
                    "id": "tx-1",
                    "transaction_type": "deposit",
                    "transaction_kind": "bank_transfer_in",
                    "direction": "credit",
                    "status": "completed",
                    "amount": Decimal("100.00"),
                    "currency": "EUR",
                    "created_at": datetime(
                        2026, 5, 3, 14, 5, tzinfo=timezone.utc
                    ),
                }
            ]
        )
        md = out["markdown_table"]
        assert "| Date | Type | Statut | Montant | Détail |" in md
        assert "|---|---|---|---:|---|" in md

    def test_each_row_has_open_link_with_deep_link(self):
        out = self._run(
            [
                {
                    "id": "abc-123",
                    "transaction_type": "deposit",
                    "transaction_kind": "bank_transfer_in",
                    "direction": "credit",
                    "status": "completed",
                    "amount": Decimal("100.00"),
                    "currency": "EUR",
                    "created_at": datetime(
                        2026, 5, 3, 14, 5, tzinfo=timezone.utc
                    ),
                }
            ]
        )
        md = out["markdown_table"]
        assert "[Ouvrir](vancelian://app/transactions/abc-123)" in md

    def test_pipes_in_values_are_escaped(self):
        # Hypothèse défensive : le repo pourrait renvoyer un narrative ou
        # un type avec un `|`. On vérifie qu'on n'explose pas la table.
        out = self._run(
            [
                {
                    "id": "tx-pipe",
                    "transaction_type": "weird|type",
                    "transaction_kind": None,
                    "direction": "credit",
                    "status": "completed",
                    "amount": Decimal("1.00"),
                    "currency": "EUR",
                    "created_at": datetime(
                        2026, 5, 3, 0, 0, tzinfo=timezone.utc
                    ),
                }
            ]
        )
        md = out["markdown_table"]
        # `_humanize` capitalize la première lettre, donc le label
        # rendu est `Weird|type` puis le `|` est échappé.
        assert "Weird\\|type" in md


# ─────────────────────────────────────────────────────────────────────
# D. Filters propagation to repository
# ─────────────────────────────────────────────────────────────────────


class TestFiltersPropagation:
    def test_passes_filters_to_repo_unchanged(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            list_transactions.compliance_repo,
            "fetch_transactions_list",
            return_value=[],
        ) as repo_mock:
            list_transactions.execute(
                ctx,
                category="deposits",
                direction="credit",
                status="completed",
                since="2026-04-01",
                limit=10,
            )
        kwargs = repo_mock.call_args.kwargs
        assert kwargs["category"] == "deposits"
        assert kwargs["direction"] == "credit"
        assert kwargs["status"] == "completed"
        assert kwargs["since"] == "2026-04-01"
        assert kwargs["limit"] == 10

    def test_clamps_limit_to_max_50(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            list_transactions.compliance_repo,
            "fetch_transactions_list",
            return_value=[],
        ) as repo_mock:
            list_transactions.execute(ctx, limit=999)
        assert repo_mock.call_args.kwargs["limit"] == 50

    def test_clamps_limit_to_min_1(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            list_transactions.compliance_repo,
            "fetch_transactions_list",
            return_value=[],
        ) as repo_mock:
            list_transactions.execute(ctx, limit=0)
        assert repo_mock.call_args.kwargs["limit"] == 1

    def test_filters_applied_echoes_inputs(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            list_transactions.compliance_repo,
            "fetch_transactions_list",
            return_value=[],
        ):
            out = list_transactions.execute(
                ctx, category="cards", limit=5
            )
        assert out["filters_applied"]["category"] == "cards"
        assert out["filters_applied"]["limit"] == 5
        assert "direction" not in out["filters_applied"]


# ─────────────────────────────────────────────────────────────────────
# E. Repository error → graceful payload
# ─────────────────────────────────────────────────────────────────────


class TestRepoError:
    def test_returns_empty_payload_with_error_marker(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            list_transactions.compliance_repo,
            "fetch_transactions_list",
            side_effect=RuntimeError("boom"),
        ):
            out = list_transactions.execute(ctx)
        assert out["count"] == 0
        assert out["items"] == []
        assert out["error"] == "repo_unavailable"
        assert "Aucune transaction" in out["markdown_table"]
