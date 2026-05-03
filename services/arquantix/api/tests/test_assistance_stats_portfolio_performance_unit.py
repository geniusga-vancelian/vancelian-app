"""Tests unitaires du tool ``stats_portfolio_performance`` — Phase 2c.5 Lot 2.

Couvre :
  - Absence de ``client_id`` → payload neutre safe.
  - Format ``markdown_table`` : 6 lignes (NAV, Capital net, PnL réalisé,
    PnL latent, PnL total, Performance), header + séparateur.
  - Formatage FR du montant : groupement avec narrow no-break space
    (``\u202f``), 2 décimales si non rondes, pas de décimales si entier.
  - Signe explicite ``+`` / ``-`` sur les PnL ; pas de signe sur la NAV
    ni le capital net déposé.
  - Performance % : ``+12,34 %``, ``-5,00 %``, ``0,00 %``, ``n/a``.
  - Cas portefeuille vide → message texte, pas de tableau.
  - Erreur repo → ``error: repo_unavailable`` + payload neutre.

Aucune dépendance Postgres : on mocke
``compliance_repo.fetch_portfolio_performance``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.assistance.agents.tools.compliance import (
    stats_portfolio_performance,
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
        correlation_id="t-stats-perf",
    )


def _agg(
    *,
    current_value=0.0,
    net_deposits=0.0,
    realized=0.0,
    unrealized=0.0,
    total_pnl=None,
    perf_pct=None,
    currency="EUR",
):
    if total_pnl is None:
        total_pnl = realized + unrealized
    return {
        "currency": currency,
        "current_value": current_value,
        "net_deposits": net_deposits,
        "realized_pnl": realized,
        "unrealized_pnl": unrealized,
        "total_pnl": total_pnl,
        "performance_pct": perf_pct,
    }


# ─────────────────────────────────────────────────────────────────────
# A. No client_id → safe empty
# ─────────────────────────────────────────────────────────────────────


class TestNoClientContext:
    def test_returns_empty_payload(self):
        out = stats_portfolio_performance.execute(_ctx(client_id=None))
        assert out["current_value"] == "0"
        assert out["net_deposits"] == "0"
        assert out["total_pnl"] == "0"
        assert "vide" in out["markdown_table"]


# ─────────────────────────────────────────────────────────────────────
# B. Markdown rendering — happy path
# ─────────────────────────────────────────────────────────────────────


class TestMarkdownRendering:
    def _run(self, agg):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_portfolio_performance.compliance_repo,
            "fetch_portfolio_performance",
            return_value=agg,
        ):
            return stats_portfolio_performance.execute(ctx)

    def test_table_contains_six_data_rows(self):
        out = self._run(
            _agg(
                current_value=50000.00,
                net_deposits=45000.00,
                realized=2000.00,
                unrealized=3000.00,
                perf_pct=11.11,
            )
        )
        md = out["markdown_table"]
        assert "**Valeur actuelle**" in md
        assert "Capital net déposé" in md
        assert "Plus-values réalisées" in md
        assert "Plus-values latentes" in md
        assert "_PnL total_" in md
        assert "_Performance_" in md

    def test_header_and_separator(self):
        out = self._run(_agg(current_value=100, net_deposits=80))
        md = out["markdown_table"]
        assert "| Indicateur | Valeur |" in md
        assert "|---|---:|" in md

    def test_nav_has_no_sign(self):
        out = self._run(_agg(current_value=12345.67, net_deposits=10000))
        md = out["markdown_table"]
        # NAV ne doit pas porter +/- en préfixe.
        assert "**Valeur actuelle** | 12" in md.replace("\u202f", " ")
        # Pas de "+12 345" ni "-12 345" pour la NAV.
        assert "+12\u202f345" not in md
        # Le motif `12 345,67 €` doit être présent.
        assert "12\u202f345,67" in md

    def test_realized_positive_has_plus_sign(self):
        out = self._run(_agg(current_value=100, net_deposits=50, realized=200))
        md = out["markdown_table"]
        assert "+200" in md.replace("\u202f", "")

    def test_realized_negative_has_minus_sign(self):
        out = self._run(_agg(current_value=100, net_deposits=200, realized=-50))
        md = out["markdown_table"]
        assert "-50" in md.replace("\u202f", "")

    def test_total_pnl_uses_total_field_not_recomputed(self):
        # Si total_pnl est explicitement fourni, on l'utilise tel quel
        # (pas de recompute realized + unrealized).
        out = self._run(
            _agg(
                current_value=1000,
                net_deposits=900,
                realized=10,
                unrealized=10,
                total_pnl=42.0,  # ≠ 20 = realized + unrealized
            )
        )
        md = out["markdown_table"]
        assert "+42" in md.replace("\u202f", "")

    def test_thousand_grouping_uses_thin_space(self):
        out = self._run(
            _agg(current_value=1234567.89, net_deposits=1000000)
        )
        md = out["markdown_table"]
        assert "1\u202f234\u202f567" in md

    def test_integer_amount_omits_decimals(self):
        out = self._run(_agg(current_value=45000.00, net_deposits=40000.00))
        md = out["markdown_table"]
        assert "45\u202f000" in md
        assert ",00" not in md

    def test_eur_symbol_used(self):
        out = self._run(_agg(current_value=100, net_deposits=80))
        assert "€" in out["markdown_table"]

    def test_unknown_currency_uses_iso_code(self):
        out = self._run(
            _agg(current_value=100, net_deposits=80, currency="JPY")
        )
        md = out["markdown_table"]
        assert "JPY" in md
        assert "€" not in md


# ─────────────────────────────────────────────────────────────────────
# C. Performance % formatting
# ─────────────────────────────────────────────────────────────────────


class TestPerformancePctFormat:
    def _run(self, perf_pct):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_portfolio_performance.compliance_repo,
            "fetch_portfolio_performance",
            return_value=_agg(
                current_value=100,
                net_deposits=80,
                perf_pct=perf_pct,
            ),
        ):
            return stats_portfolio_performance.execute(ctx)

    def test_positive_perf_has_plus_sign(self):
        out = self._run(12.34)
        assert "+12,34 %" in out["markdown_table"]

    def test_negative_perf_has_minus_sign(self):
        out = self._run(-5.0)
        assert "-5,00 %" in out["markdown_table"]

    def test_zero_perf(self):
        out = self._run(0.0)
        assert "0,00 %" in out["markdown_table"]

    def test_none_perf_renders_na(self):
        out = self._run(None)
        assert "n/a" in out["markdown_table"]


# ─────────────────────────────────────────────────────────────────────
# D. Empty portfolio
# ─────────────────────────────────────────────────────────────────────


class TestEmptyPortfolio:
    def test_zero_everywhere_returns_message(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_portfolio_performance.compliance_repo,
            "fetch_portfolio_performance",
            return_value=_agg(),  # all zeros
        ):
            out = stats_portfolio_performance.execute(ctx)
        assert "vide" in out["markdown_table"]
        # Pas d'header de tableau.
        assert "| Indicateur |" not in out["markdown_table"]


# ─────────────────────────────────────────────────────────────────────
# E. Repo error → graceful payload
# ─────────────────────────────────────────────────────────────────────


class TestRepoError:
    def test_returns_empty_with_error_marker(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_portfolio_performance.compliance_repo,
            "fetch_portfolio_performance",
            side_effect=RuntimeError("boom"),
        ):
            out = stats_portfolio_performance.execute(ctx)
        assert out["error"] == "repo_unavailable"
        assert "vide" in out["markdown_table"]
