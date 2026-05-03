"""Tests unitaires du tool ``stats_portfolio_allocation`` — Phase 2c.5 Lot 3.

Couvre :
  - Absence de ``client_id`` → payload safe sans embed.
  - Cas ``total_value=0`` → pas d'embed émis, summary explicite.
  - Cas happy path : embed ``portfolio_allocation_donut`` émis avec
    ``slices`` correctement sérialisées (key/label/value/percentage),
    ``summary`` chaleureux mentionnant la classe dominante.
  - Le retour LLM **ne contient pas** les valeurs en € brutes
    (`value` strippé), seulement les pourcentages (anti-tipping-off
    soft : valeurs déjà dans l'embed visible UI).
  - Slice unique → message simplifié *« intégralement en … »*.
  - Erreur repo → ``error: repo_unavailable``, embed non émis.

Aucune dépendance Postgres : on mocke
``compliance_repo.fetch_portfolio_allocation``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.assistance.agents.tools.compliance import (
    stats_portfolio_allocation,
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
        correlation_id="t-stats-alloc",
    )


# ─────────────────────────────────────────────────────────────────────
# A. No client_id → safe empty
# ─────────────────────────────────────────────────────────────────────


class TestNoClientContext:
    def test_returns_empty_payload_without_embed(self):
        ctx = _ctx(client_id=None)
        out = stats_portfolio_allocation.execute(ctx)
        assert out["embed_emitted"] is False
        assert out["slices"] == []
        assert "vide" in out["summary"]
        assert ctx.embeds_to_emit == []


# ─────────────────────────────────────────────────────────────────────
# B. Empty portfolio
# ─────────────────────────────────────────────────────────────────────


class TestEmptyPortfolio:
    def test_total_value_zero_does_not_emit_embed(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_portfolio_allocation.compliance_repo,
            "fetch_portfolio_allocation",
            return_value={
                "currency": "EUR",
                "total_value": 0.0,
                "slices": [],
            },
        ):
            out = stats_portfolio_allocation.execute(ctx)
        assert out["embed_emitted"] is False
        assert "vide" in out["summary"]
        assert ctx.embeds_to_emit == []


# ─────────────────────────────────────────────────────────────────────
# C. Happy path — embed emission + summary
# ─────────────────────────────────────────────────────────────────────


class TestHappyPath:
    def _slices_three(self):
        return [
            {
                "key": "fiat",
                "label": "Cash (EUR)",
                "value": 5000.00,
                "percentage": 25.0,
            },
            {
                "key": "crypto_direct",
                "label": "Crypto en direct",
                "value": 12000.00,
                "percentage": 60.0,
            },
            {
                "key": "bundles",
                "label": "Bundles",
                "value": 3000.00,
                "percentage": 15.0,
            },
        ]

    def _run(self, slices, total=20000.0):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_portfolio_allocation.compliance_repo,
            "fetch_portfolio_allocation",
            return_value={
                "currency": "EUR",
                "total_value": total,
                "slices": slices,
            },
        ):
            out = stats_portfolio_allocation.execute(ctx)
        return ctx, out

    def test_embed_emitted_once(self):
        ctx, _out = self._run(self._slices_three())
        assert len(ctx.embeds_to_emit) == 1
        assert ctx.embeds_to_emit[0]["type"] == "portfolio_allocation_donut"

    def test_embed_contains_currency_and_total(self):
        ctx, _ = self._run(self._slices_three())
        emb = ctx.embeds_to_emit[0]
        assert emb["currency"] == "EUR"
        assert emb["total_value"] == 20000.0

    def test_embed_slices_serialized_with_value_and_percentage(self):
        ctx, _ = self._run(self._slices_three())
        emb = ctx.embeds_to_emit[0]
        assert len(emb["slices"]) == 3
        assert emb["slices"][0]["key"] == "fiat"
        assert emb["slices"][0]["label"] == "Cash (EUR)"
        assert emb["slices"][0]["value"] == 5000.0
        assert emb["slices"][0]["percentage"] == 25.0

    def test_embed_summary_mentions_dominant_class(self):
        ctx, _ = self._run(self._slices_three())
        emb = ctx.embeds_to_emit[0]
        # Crypto en direct = 60 % → dominante.
        assert "Crypto en direct" in emb["summary"]
        assert "60" in emb["summary"]

    def test_embed_summary_includes_total_value(self):
        ctx, _ = self._run(self._slices_three())
        emb = ctx.embeds_to_emit[0]
        # 20 000 € (avec narrow no-break space).
        assert "20\u202f000" in emb["summary"]
        assert "€" in emb["summary"]

    def test_llm_payload_strips_raw_values(self):
        # Le retour visible LLM expose les % mais pas les € bruts
        # par slice (`value` ne doit PAS être dans le retour LLM,
        # contrairement à l'embed UI).
        _, out = self._run(self._slices_three())
        for slice_ in out["slices"]:
            assert "value" not in slice_
            assert "percentage" in slice_

    def test_embed_emitted_flag_in_llm_payload(self):
        _, out = self._run(self._slices_three())
        assert out["embed_emitted"] is True


# ─────────────────────────────────────────────────────────────────────
# D. Single slice (only one class non-zero)
# ─────────────────────────────────────────────────────────────────────


class TestSingleSlice:
    def test_summary_uses_integral_phrasing(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_portfolio_allocation.compliance_repo,
            "fetch_portfolio_allocation",
            return_value={
                "currency": "EUR",
                "total_value": 1000.0,
                "slices": [
                    {
                        "key": "fiat",
                        "label": "Cash (EUR)",
                        "value": 1000.0,
                        "percentage": 100.0,
                    },
                ],
            },
        ):
            stats_portfolio_allocation.execute(ctx)
        emb = ctx.embeds_to_emit[0]
        # « intégralement en cash (eur) » (lowercase normalisé).
        assert "intégralement" in emb["summary"]
        assert "cash (eur)" in emb["summary"].lower()


# ─────────────────────────────────────────────────────────────────────
# E. Repo error → graceful payload
# ─────────────────────────────────────────────────────────────────────


class TestRepoError:
    def test_returns_error_marker_and_no_embed(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_portfolio_allocation.compliance_repo,
            "fetch_portfolio_allocation",
            side_effect=RuntimeError("boom"),
        ):
            out = stats_portfolio_allocation.execute(ctx)
        assert out["error"] == "repo_unavailable"
        assert out["embed_emitted"] is False
        assert ctx.embeds_to_emit == []
