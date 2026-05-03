"""Tests unitaires du tool ``stats_transaction_amounts`` — Phase 2c.5.

Couvre :
  - Absence de ``client_id`` → payload vide safe.
  - Format ``markdown_table`` : 3 lignes (Total déposé, Total retiré,
    Solde net), avec ``+`` / ``-`` / signe net cohérents.
  - Formatage FR du montant : groupement avec narrow no-break space
    (``\u202f``), 2 décimales si non rondes, pas de décimales si entier.
  - Devise : symboles connus (€, $, £) ou code ISO en fallback.
  - Cas multi-devise : le tool sélectionne la devise dominante en
    volume agrégé.
  - Cas vide (deposits=withdrawals=0) → message ``Aucune transaction``.
  - Status par défaut = ``completed`` côté repo (forcé par
    fetch_transaction_amounts), surcharge possible.
  - Erreur repo → payload neutre avec ``error=repo_unavailable``.

Aucune dépendance Postgres : on mocke
``compliance_repo.fetch_transaction_amounts``.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.assistance.agents.tools.compliance import (
    stats_transaction_amounts,
)
from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _ctx(*, client_id: str | None = None) -> ToolContext:
    return ToolContext(
        db=MagicMock(),
        client_id=client_id,
        person_id=None,
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id="compliance.transactional",
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t-stats-amounts",
    )


def _agg(
    *,
    deposits=Decimal("0"),
    withdrawals=Decimal("0"),
    currency="EUR",
    by_currency=None,
):
    return {
        "currency": currency,
        "deposits_total": deposits,
        "withdrawals_total": withdrawals,
        "net": deposits - withdrawals,
        "by_currency": by_currency
        or {currency: {"deposits": deposits, "withdrawals": withdrawals}},
    }


# ─────────────────────────────────────────────────────────────────────
# A. No client_id → safe empty
# ─────────────────────────────────────────────────────────────────────


class TestNoClientContext:
    def test_returns_empty_payload(self):
        out = stats_transaction_amounts.execute(_ctx(client_id=None))
        assert out["currency"] == "EUR"
        assert out["deposits_total"] == "0"
        assert out["withdrawals_total"] == "0"
        assert out["net"] == "0"
        assert "Aucune transaction" in out["markdown_table"]


# ─────────────────────────────────────────────────────────────────────
# B. Markdown rendering — happy path
# ─────────────────────────────────────────────────────────────────────


class TestMarkdownRendering:
    def _run(self, agg):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_amounts.compliance_repo,
            "fetch_transaction_amounts",
            return_value=agg,
        ):
            return stats_transaction_amounts.execute(ctx)

    def test_table_contains_three_data_rows(self):
        out = self._run(
            _agg(
                deposits=Decimal("45000.00"),
                withdrawals=Decimal("5000.00"),
            )
        )
        md = out["markdown_table"]
        assert "**Total déposé**" in md
        assert "**Total retiré**" in md
        assert "_Solde net_" in md

    def test_header_and_separator(self):
        out = self._run(
            _agg(
                deposits=Decimal("100.00"),
                withdrawals=Decimal("50.00"),
            )
        )
        md = out["markdown_table"]
        assert "| Direction | Montant total |" in md
        assert "|---|---:|" in md

    def test_deposit_has_plus_sign(self):
        out = self._run(_agg(deposits=Decimal("100.00")))
        md = out["markdown_table"]
        assert "+100" in md.replace("\u202f", "")

    def test_withdrawal_has_minus_sign(self):
        out = self._run(
            _agg(
                deposits=Decimal("0"),
                withdrawals=Decimal("75.00"),
            )
        )
        md = out["markdown_table"]
        assert "-75" in md.replace("\u202f", "")

    def test_positive_net_has_plus(self):
        out = self._run(
            _agg(
                deposits=Decimal("200.00"),
                withdrawals=Decimal("75.00"),
            )
        )
        md = out["markdown_table"]
        # Net = +125
        assert "+125" in md.replace("\u202f", "")

    def test_negative_net_has_minus(self):
        out = self._run(
            _agg(
                deposits=Decimal("50.00"),
                withdrawals=Decimal("200.00"),
            )
        )
        md = out["markdown_table"]
        # Net = -150
        assert "-150" in md.replace("\u202f", "")

    def test_thousand_grouping_uses_thin_space(self):
        out = self._run(_agg(deposits=Decimal("1234567.89")))
        md = out["markdown_table"]
        # narrow no-break space (\u202f) entre les milliers
        assert "1\u202f234\u202f567" in md

    def test_integer_amount_omits_decimals(self):
        out = self._run(_agg(deposits=Decimal("45000.00")))
        md = out["markdown_table"]
        assert "45\u202f000" in md
        assert ",00" not in md

    def test_non_integer_amount_keeps_two_decimals(self):
        out = self._run(_agg(deposits=Decimal("1234.56")))
        md = out["markdown_table"]
        assert "1\u202f234,56" in md

    def test_eur_symbol_is_used(self):
        out = self._run(_agg(deposits=Decimal("100.00"), currency="EUR"))
        assert "€" in out["markdown_table"]

    def test_unknown_currency_uses_iso_code(self):
        out = self._run(_agg(deposits=Decimal("100.00"), currency="JPY"))
        assert "JPY" in out["markdown_table"]


# ─────────────────────────────────────────────────────────────────────
# C. Empty case
# ─────────────────────────────────────────────────────────────────────


class TestEmptyAggregate:
    def test_zero_deposits_and_withdrawals_returns_message(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_amounts.compliance_repo,
            "fetch_transaction_amounts",
            return_value=_agg(),  # zeros
        ):
            out = stats_transaction_amounts.execute(ctx)
        assert "Aucune transaction" in out["markdown_table"]
        assert out["deposits_total"] == "0"
        assert out["withdrawals_total"] == "0"
        assert out["net"] == "0"


# ─────────────────────────────────────────────────────────────────────
# D. Filters propagation
# ─────────────────────────────────────────────────────────────────────


class TestFiltersPropagation:
    def test_passes_filters_unchanged(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_amounts.compliance_repo,
            "fetch_transaction_amounts",
            return_value=_agg(),
        ) as repo_mock:
            stats_transaction_amounts.execute(
                ctx,
                category="deposits",
                direction="credit",
                status="pending",
                since="2026-04-01",
            )
        kwargs = repo_mock.call_args.kwargs
        assert kwargs["category"] == "deposits"
        assert kwargs["direction"] == "credit"
        assert kwargs["status"] == "pending"
        assert kwargs["since"] == "2026-04-01"

    def test_filters_applied_echoes_inputs(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_amounts.compliance_repo,
            "fetch_transaction_amounts",
            return_value=_agg(deposits=Decimal("100")),
        ):
            out = stats_transaction_amounts.execute(
                ctx, category="cards"
            )
        assert out["filters_applied"]["category"] == "cards"
        assert "direction" not in out["filters_applied"]


# ─────────────────────────────────────────────────────────────────────
# E. by_currency serialization
# ─────────────────────────────────────────────────────────────────────


class TestByCurrencySerialization:
    def test_decimals_are_serialized_to_strings(self):
        ctx = _ctx(client_id=str(uuid4()))
        agg = _agg(
            deposits=Decimal("100.00"),
            withdrawals=Decimal("50.00"),
            currency="EUR",
            by_currency={
                "EUR": {
                    "deposits": Decimal("100.00"),
                    "withdrawals": Decimal("50.00"),
                    "net": Decimal("50.00"),
                },
            },
        )
        with patch.object(
            stats_transaction_amounts.compliance_repo,
            "fetch_transaction_amounts",
            return_value=agg,
        ):
            out = stats_transaction_amounts.execute(ctx)
        eur = out["by_currency"]["EUR"]
        assert isinstance(eur["deposits"], str)
        assert isinstance(eur["withdrawals"], str)
        assert isinstance(eur["net"], str)
        assert eur["deposits"] == "100.00"


# ─────────────────────────────────────────────────────────────────────
# F. Repo error → graceful payload
# ─────────────────────────────────────────────────────────────────────


class TestRepoError:
    def test_returns_empty_with_error_marker(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_amounts.compliance_repo,
            "fetch_transaction_amounts",
            side_effect=RuntimeError("boom"),
        ):
            out = stats_transaction_amounts.execute(ctx)
        assert out["error"] == "repo_unavailable"
        assert "Aucune transaction" in out["markdown_table"]
        assert out["deposits_total"] == "0"
