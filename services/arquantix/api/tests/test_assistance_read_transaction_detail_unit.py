"""Tests unitaires du tool ``read_transaction_detail`` — Phase 2c.4.

Couvre :

  - Génération du `summary` selon `kind` + `is_inbound` + `status`.
  - Mention du problème uniquement si statut ≠ completed.
  - Format du montant FR (espace fin, pas de décimales si entier rond).
  - Anti-tipping-off : `amount` et `currency` strippés du retour LLM
    même si présents dans le détail repo.
  - Absence de `summary` quand la donnée est insuffisante
    (date manquante).

Aucun accès Postgres : ``compliance_repo.fetch_transaction_detail``
est mocké.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.assistance.agents.tools.compliance import read_transaction_detail
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
        correlation_id="t-detail",
    )


def _detail(**overrides):
    base = {
        "transaction_id": "11111111-1111-1111-1111-111111111111",
        "status": "completed",
        "kind": "bank_transfer_in",
        "source": "cash",
        "created_at": "2026-05-03T02:34:00+00:00",
        "updated_at": "2026-05-03T02:34:00+00:00",
        "is_inbound": True,
        "amount": Decimal("45000.00"),
        "currency": "EUR",
    }
    base.update(overrides)
    return base


def _run(detail):
    ctx = _ctx(client_id=str(uuid4()))
    with patch.object(
        read_transaction_detail.compliance_repo,
        "fetch_transaction_detail",
        return_value=detail,
    ):
        result = read_transaction_detail.execute(
            ctx, transaction_id=str(detail["transaction_id"])
        )
    embed = ctx.embeds_to_emit[0] if ctx.embeds_to_emit else None
    return result, embed


# ─────────────────────────────────────────────────────────────────────
# A. Composition du summary
# ─────────────────────────────────────────────────────────────────────


class TestSummaryComposition:
    def test_completed_deposit_no_problem_phrase(self):
        _, embed = _run(_detail())
        assert embed is not None
        s = embed["summary"]
        assert "dépôt par virement bancaire" in s
        assert "45\u202f000 €" in s
        assert "3 mai 2026" in s
        # Status completed → pas de mention de problème.
        assert "attente" not in s
        assert "échoué" not in s
        assert s.endswith("Voici les détails ci-dessous.")

    def test_pending_status_adds_problem_phrase(self):
        _, embed = _run(_detail(status="pending"))
        assert "actuellement en attente" in embed["summary"]

    def test_on_hold_status_adds_problem_phrase(self):
        _, embed = _run(_detail(status="on_hold"))
        assert "bloqué pour vérification" in embed["summary"]

    def test_failed_status_adds_problem_phrase(self):
        _, embed = _run(_detail(status="failed"))
        assert "échoué" in embed["summary"]

    def test_card_in_uses_card_label(self):
        _, embed = _run(_detail(kind="card_in"))
        assert "dépôt par carte" in embed["summary"]

    def test_outbound_uses_retrait_label(self):
        _, embed = _run(_detail(kind="bank_transfer_out", is_inbound=False))
        assert "virement sortant" in embed["summary"]

    def test_unknown_kind_falls_back(self):
        _, embed = _run(_detail(kind="weird_kind", is_inbound=True))
        assert "dépôt" in embed["summary"]

    def test_amount_with_decimals(self):
        _, embed = _run(_detail(amount=Decimal("123.45")))
        assert "123,45 €" in embed["summary"]

    def test_amount_round_no_decimals(self):
        _, embed = _run(_detail(amount=Decimal("1000.00")))
        assert "1\u202f000 €" in embed["summary"]
        assert "1\u202f000,00 €" not in embed["summary"]

    def test_unknown_currency_falls_back_to_iso(self):
        _, embed = _run(_detail(currency="JPY"))
        assert "JPY" in embed["summary"]


# ─────────────────────────────────────────────────────────────────────
# B. Anti-tipping-off : strip avant retour LLM
# ─────────────────────────────────────────────────────────────────────


class TestAntiTippingOff:
    def test_amount_not_in_llm_result(self):
        result, _ = _run(_detail())
        assert "amount" not in result

    def test_currency_not_in_llm_result(self):
        result, _ = _run(_detail())
        assert "currency" not in result

    def test_status_kind_dates_remain_in_llm_result(self):
        result, _ = _run(_detail())
        # Les champs safe restent visibles au LLM.
        assert result["status"] == "completed"
        assert result["kind"] == "bank_transfer_in"
        assert result["created_at"] is not None
        assert result["is_inbound"] is True


# ─────────────────────────────────────────────────────────────────────
# C. Embed structure
# ─────────────────────────────────────────────────────────────────────


class TestEmbedStructure:
    def test_embed_has_two_actions(self):
        _, embed = _run(_detail())
        kinds = {a["kind"] for a in embed["actions"]}
        assert "view_transaction_detail" in kinds
        assert "download_transaction_statement" in kinds

    def test_embed_includes_status_kind_hints(self):
        _, embed = _run(_detail())
        assert embed["status"] == "completed"
        assert embed["kind"] == "bank_transfer_in"
        assert embed["is_inbound"] is True

    def test_embed_summary_present_when_data_complete(self):
        _, embed = _run(_detail())
        assert "summary" in embed
        assert embed["summary"]

    def test_embed_summary_absent_when_no_date_and_no_amount(self):
        # Sans date NI montant le récap est trop creux ; on s'abstient
        # et la carte parle seule (juste le tableau et les actions).
        _, embed = _run(
            _detail(
                created_at=None,
                amount=None,
                kind=None,
                is_inbound=None,
            )
        )
        assert "summary" not in embed


# ─────────────────────────────────────────────────────────────────────
# D. Erreurs / fallback
# ─────────────────────────────────────────────────────────────────────


class TestErrorPaths:
    def test_no_client_context_returns_error(self):
        ctx = _ctx(client_id=None)
        result = read_transaction_detail.execute(
            ctx, transaction_id="11111111-1111-1111-1111-111111111111"
        )
        assert result["error"] == "no_client_context"
        # Pas d'embed émis si pas de client.
        assert ctx.embeds_to_emit == []

    def test_missing_transaction_id(self):
        ctx = _ctx(client_id=str(uuid4()))
        result = read_transaction_detail.execute(ctx, transaction_id="")
        assert result["error"] == "missing_transaction_id"

    def test_repo_error_returns_error_no_embed(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            read_transaction_detail.compliance_repo,
            "fetch_transaction_detail",
            side_effect=RuntimeError("DB down"),
        ):
            result = read_transaction_detail.execute(
                ctx, transaction_id="11111111-1111-1111-1111-111111111111"
            )
        assert result["error"] == "repo_unavailable"
        assert ctx.embeds_to_emit == []

    def test_not_found_no_embed(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            read_transaction_detail.compliance_repo,
            "fetch_transaction_detail",
            return_value={
                **_detail(),
                "error": "not_found",
            },
        ):
            result = read_transaction_detail.execute(
                ctx, transaction_id="11111111-1111-1111-1111-111111111111"
            )
        # Le tool propage le not_found.
        assert result.get("error") == "not_found"
        # `amount` quand même strippé même quand error présent (sécurité).
        assert "amount" not in result
        # Aucun embed (le détail n'est pas valide).
        assert ctx.embeds_to_emit == []
