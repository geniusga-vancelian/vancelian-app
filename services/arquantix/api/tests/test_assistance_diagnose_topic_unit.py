"""Tests unitaires du tool `diagnose_compliance_topic` — Phase 2b.

Couvre la cascade de classification :
  - registration (KYC pas approuvé / steps incomplets / account suspendu)
  - remediation (KYC ok + signal doc/AML)
  - transactional (mots-clés OU transactions failed)
  - general (fallback)
  - secondary_topics (multi-trigger)
  - next_recommended_action (mapping topic × état)
  - context_for_llm (champs publics seulement)

Spec : `docs/arquantix/COMPLIANCE_TOPICS.md` § 2.3.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance.agents.tools.compliance import (
    diagnose_compliance_topic,
)
from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _ctx(
    *,
    client_id: str | None = "11111111-1111-1111-1111-111111111111",
    person_id: str | None = "22222222-2222-2222-2222-222222222222",
    actor_kind: ActorKind = ActorKind.CUSTOMER,
) -> ToolContext:
    return ToolContext(
        db=MagicMock(),
        client_id=client_id,
        person_id=person_id,
        user_id=42,
        actor_kind=actor_kind,
        agent_id="compliance",
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t-diag",
    )


def _patch_repo(
    *,
    status: dict | None = None,
    safe_signals: dict | None = None,
    registration: dict | None = None,
    documents: dict | None = None,
    transactions: dict | None = None,
):
    """Patch les 4 fonctions du repo pour le tour du tool."""
    from services.assistance.agents.tools.compliance import (
        diagnose_compliance_topic as mod,
    )

    return [
        patch.object(
            mod.compliance_repo,
            "fetch_compliance_state_snapshot",
            return_value={
                "status": status or {},
                "safe_signals": safe_signals or {},
            },
        ),
        patch.object(
            mod.compliance_repo,
            "fetch_registration_progress",
            return_value=registration or {},
        ),
        patch.object(
            mod.compliance_repo,
            "fetch_documents_summary",
            return_value=documents or {},
        ),
        patch.object(
            mod.compliance_repo,
            "fetch_transactions_summary",
            return_value=transactions or {},
        ),
    ]


def _run(ctx: ToolContext, *, hint: str = "", **repo_kwargs):
    """Invoque le tool sous patches."""
    patches = _patch_repo(**repo_kwargs)
    for p in patches:
        p.start()
    try:
        return diagnose_compliance_topic.execute(
            ctx, user_message_hint=hint
        )
    finally:
        for p in patches:
            p.stop()


# ─────────────────────────────────────────────────────────────────────────
# A. Topic registration
# ─────────────────────────────────────────────────────────────────────────


class TestRegistrationTopic:
    def test_kyc_pending(self):
        result = _run(
            _ctx(),
            status={"kyc_status": "pending", "account_state": "ACTIVE"},
            registration={"completed_steps": 2, "total_steps_recorded": 5},
        )
        assert result["dominant_topic"] == "registration"
        assert result["confidence"] >= 0.8
        assert "kyc_status=pending" in result["triggers_used"]
        assert result["context_for_llm"]["kyc_complete"] is False

    def test_account_partial(self):
        result = _run(
            _ctx(),
            status={"kyc_status": "approved", "account_state": "PARTIAL"},
        )
        assert result["dominant_topic"] == "registration"
        assert "account_state=PARTIAL" in result["triggers_used"]

    def test_steps_incomplete_even_if_kyc_approved(self):
        result = _run(
            _ctx(),
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            registration={"completed_steps": 3, "total_steps_recorded": 5},
        )
        assert result["dominant_topic"] == "registration"

    def test_recommended_action_resume_when_session_active(self):
        result = _run(
            _ctx(),
            status={"kyc_status": "pending", "account_state": "ACTIVE"},
            registration={
                "session_status": "in_progress",
                "current_step_id": "step_3",
                "completed_steps": 2,
                "total_steps_recorded": 5,
            },
        )
        action = result["next_recommended_action"]
        assert action is not None
        assert action["kind"] == "resume_registration"
        assert action["deep_link"] == "vancelian://app/registration_resume"

    def test_recommended_action_first_deposit_when_kyc_done_no_orders(self):
        # KYC approved + 0 order + 1 step manquant → dispatched as
        # registration ; on propose le 1er dépôt.
        result = _run(
            _ctx(),
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            registration={
                "session_status": "completed",
                "completed_steps": 4,
                "total_steps_recorded": 5,
            },
            transactions={"orders_count": 0},
        )
        # On force registration via steps incomplets…
        assert result["dominant_topic"] == "registration"
        # … pas de session active → fallback deposit_funds.
        action = result["next_recommended_action"]
        assert action is not None
        assert action["kind"] == "deposit_funds"


# ─────────────────────────────────────────────────────────────────────────
# B. Topic remediation
# ─────────────────────────────────────────────────────────────────────────


class TestRemediationTopic:
    def test_kyc_ok_doc_required(self):
        result = _run(
            _ctx(),
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            safe_signals={"requires_doc_upload": True},
        )
        assert result["dominant_topic"] == "remediation"
        assert "requires_doc_upload=true" in result["triggers_used"]

    def test_kyc_ok_step_up_required(self):
        result = _run(
            _ctx(),
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            safe_signals={"requires_step_up": True},
        )
        assert result["dominant_topic"] == "remediation"

    def test_kyc_ok_doc_rejected(self):
        result = _run(
            _ctx(),
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            documents={"by_status": {"rejected": 1, "approved": 0}},
        )
        assert result["dominant_topic"] == "remediation"
        assert "documents_rejected_present" in result["triggers_used"]

    def test_recommended_action_view_account_info(self):
        result = _run(
            _ctx(),
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            safe_signals={"requires_doc_upload": True},
        )
        action = result["next_recommended_action"]
        assert action is not None
        # Phase 2b — pas d'écran upload : on redirige vers le profil.
        assert action["kind"] == "view_account_info"

    # ── Phase 2b fix #1 : détection par mots-clés FR/EN ──────────────
    @pytest.mark.parametrize(
        "hint",
        [
            "pourquoi vous me demandez encore un justificatif ?",
            "il me faut quel document supplémentaire ?",
            "vous voulez quoi comme justification ?",
            "je dois fournir une preuve de quoi ?",
            "vous me demandez une nouvelle pièce ?",
            "j'ai besoin d'attestation pour quoi ?",
            "comment uploader un document ?",
            "régulariser mon dossier",
            "I need to upload a document",
            "why do you require this proof again",
        ],
    )
    def test_keyword_hint_classifies_remediation(self, hint):
        # KYC approved + ACTIVE + zéro signal DB + AUCUN keyword
        # transactional → remediation par keyword uniquement.
        result = _run(
            _ctx(),
            hint=hint,
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
        )
        assert result["dominant_topic"] == "remediation", (
            f"hint={hint!r} → topic={result['dominant_topic']}"
        )
        assert "user_message_keyword_match" in result["triggers_used"]
        # Detection purement keyword → confiance baissée à 0.7.
        assert result["confidence"] == 0.7

    # ── Phase 2b fix #8 : « vérifier » N'EST PLUS un keyword rem ──────
    @pytest.mark.parametrize(
        "hint",
        [
            "vérifier",
            "je voudrais vérifier mon compte",
            "peux-tu vérifier pour moi ?",
        ],
    )
    def test_verify_alone_is_not_remediation(self, hint):
        # "Vérifier" tout seul est trop générique pour déclencher
        # remediation. Sans autre keyword AML/doc, on retombe sur general.
        result = _run(
            _ctx(),
            hint=hint,
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
        )
        assert result["dominant_topic"] == "general", (
            f"hint={hint!r} → topic={result['dominant_topic']}"
        )

    def test_db_signal_takes_precedence_over_keyword_confidence(self):
        # Avec un signal DB (`requires_doc_upload`) la confiance reste à 0.8.
        result = _run(
            _ctx(),
            hint="je dois fournir un document ?",
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            safe_signals={"requires_doc_upload": True},
        )
        assert result["dominant_topic"] == "remediation"
        assert result["confidence"] == 0.8
        # Le signal DB ET le keyword hint doivent tous deux apparaître
        # dans triggers_used (pour observabilité fine).
        assert "requires_doc_upload=true" in result["triggers_used"]
        assert "user_message_keyword_match" in result["triggers_used"]

    # ── Phase 2b fix #8 : transactional gagne sur rem-keyword-only ───
    @pytest.mark.parametrize(
        "hint",
        [
            "vérifier mes transactions",
            "voir mes transactions",
            "je veux savoir si mon dépôt est arrivé",
            "où en est mon virement ?",
            "regarde mon retrait s'il te plaît",
        ],
    )
    def test_transactional_keyword_wins_over_remediation_keyword(self, hint):
        """Quand le user mentionne explicitement « transactions »,
        « dépôt », « virement », c'est un signal sur-précis qui doit
        gagner sur un éventuel co-match remediation par keyword (ex.
        anciennement « vérifier »).
        """
        result = _run(
            _ctx(),
            hint=hint,
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            transactions={"orders_count": 2, "by_status": {"completed": 2}},
        )
        assert result["dominant_topic"] == "transactional", (
            f"hint={hint!r} → topic={result['dominant_topic']}"
        )

    def test_transactional_with_db_remediation_signal_keeps_remediation(self):
        """Inversement : si la DB indique objectivement un doc à
        fournir (`requires_doc_upload`), remediation garde priorité
        même quand le user mentionne aussi « transactions ».
        """
        result = _run(
            _ctx(),
            hint="vérifier mes transactions",
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            safe_signals={"requires_doc_upload": True},
            transactions={"orders_count": 2},
        )
        assert result["dominant_topic"] == "remediation"
        # Mais transactional doit apparaître en secondary.
        assert "transactional" in result["secondary_topics"]
        assert "requires_doc_upload=true" in result["triggers_used"]

    def test_transactional_with_rem_keyword_logs_remediation_secondary(self):
        """Un cas mixte : « voir mes transactions et mes documents »
        → topic dominant = transactional (keyword TX explicite),
        remediation en secondary (keyword doc).
        """
        result = _run(
            _ctx(),
            hint="voir mes transactions et mes documents",
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            transactions={"orders_count": 1},
        )
        assert result["dominant_topic"] == "transactional"
        assert "remediation" in result["secondary_topics"]
        # Les triggers TX + keyword rem doivent tous apparaître.
        assert "user_message_keyword_match" in result["triggers_used"]

    def test_keyword_doc_does_not_shadow_registration_pending(self):
        # Si le client est encore en KYC pending et demande un
        # justificatif, on doit dispatcher vers `registration` (cascade
        # is_reg > is_rem > is_tx). Mais on log `remediation` en secondary.
        result = _run(
            _ctx(),
            hint="quel justificatif vous me demandez encore ?",
            status={"kyc_status": "pending", "account_state": "ACTIVE"},
            registration={"completed_steps": 2, "total_steps_recorded": 5},
        )
        assert result["dominant_topic"] == "registration"
        assert "remediation" in result["secondary_topics"]
        assert "user_message_keyword_match" in result["triggers_used"]

    def test_no_remediation_keyword_no_dispatch(self):
        # Question hors-scope remediation → pas de classification.
        result = _run(
            _ctx(),
            hint="ça va ?",
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
        )
        assert result["dominant_topic"] == "general"


# ─────────────────────────────────────────────────────────────────────────
# C. Topic transactional
# ─────────────────────────────────────────────────────────────────────────


class TestTransactionalTopic:
    @pytest.mark.parametrize(
        "hint",
        [
            # Singulier
            "où en est mon dépôt ?",
            "where is my deposit",
            "mon virement bancaire est-il parti ?",
            "j'ai fait un retrait il y a 3 jours",
            "I want to know about my last transaction",
            "mon investissement est validé ?",
            # Pluriels FR — régression Phase 2c.3 (les `\b` ne créent
            # pas de boundary entre `t` et `s`, donc « dépôts » exigeait
            # `s?` dans le pattern).
            "liste tous mes dépôts",
            "donne-moi mes retraits",
            "mes virements en attente",
            "mes transactions du mois",
            "mon historique des dépôts",
            "mes opérations récentes",
            "tous mes achats et ventes",
            "mes investissements en cours",
            # Pluriels EN
            "list all my deposits",
            "all my withdrawals",
            "my recent transfers",
            "show my orders",
        ],
    )
    def test_keyword_hint_classifies_transactional(self, hint):
        result = _run(
            _ctx(),
            hint=hint,
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            transactions={"orders_count": 3},
        )
        assert result["dominant_topic"] == "transactional"
        assert "user_message_keyword_match" in result["triggers_used"]

    def test_failed_transactions_classifies_transactional(self):
        result = _run(
            _ctx(),
            hint="",
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            transactions={"by_status": {"failed": 2}, "orders_count": 5},
        )
        assert result["dominant_topic"] == "transactional"
        assert "recent_failed_transactions" in result["triggers_used"]

    def test_recommended_action_view_transactions_when_orders_exist(self):
        result = _run(
            _ctx(),
            hint="où en est mon dépôt",
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            transactions={"orders_count": 3},
        )
        action = result["next_recommended_action"]
        assert action is not None
        assert action["kind"] == "view_transactions"

    def test_recommended_action_deposit_when_no_orders(self):
        result = _run(
            _ctx(),
            hint="où est mon argent ?",
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            transactions={"orders_count": 0},
        )
        # "argent" n'est pas dans la regex — donc fallback general.
        # On va plutôt utiliser un mot-clé matché.
        result = _run(
            _ctx(),
            hint="je veux faire un dépôt",
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            transactions={"orders_count": 0},
        )
        assert result["dominant_topic"] == "transactional"
        action = result["next_recommended_action"]
        assert action is not None
        assert action["kind"] == "deposit_funds"


# ─────────────────────────────────────────────────────────────────────────
# D. Topic general (fallback)
# ─────────────────────────────────────────────────────────────────────────


class TestGeneralTopic:
    def test_kyc_ok_no_signals_no_keyword(self):
        result = _run(
            _ctx(),
            hint="bonjour, parle-moi de mon compte en général",
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            transactions={"orders_count": 0},
        )
        assert result["dominant_topic"] == "general"
        assert result["confidence"] == 0.5
        assert result["next_recommended_action"] is None

    def test_no_client_id_no_signal(self):
        result = _run(
            _ctx(client_id=None, actor_kind=ActorKind.ONBOARDING),
            hint="hello",
        )
        # Sans client_id, pas de signal de registration côté client_status.
        # registration_progress retourne vide → fallback general.
        assert result["dominant_topic"] == "general"


# ─────────────────────────────────────────────────────────────────────────
# E. Secondary topics + multi-trigger
# ─────────────────────────────────────────────────────────────────────────


class TestSecondaryTopics:
    def test_registration_with_transactional_hint(self):
        result = _run(
            _ctx(),
            hint="je veux faire un dépôt",
            status={"kyc_status": "pending", "account_state": "ACTIVE"},
            registration={"completed_steps": 1, "total_steps_recorded": 3},
            transactions={"orders_count": 0},
        )
        assert result["dominant_topic"] == "registration"
        assert "transactional" in result["secondary_topics"]


# ─────────────────────────────────────────────────────────────────────────
# F. Anti-tipping-off — context_for_llm safe
# ─────────────────────────────────────────────────────────────────────────


class TestContextForLlmSafety:
    def test_context_does_not_leak_internal_signals(self):
        # On simule un repo qui pourrait laisser fuiter (le repo lui-même
        # filtre déjà ; on vérifie ici que le tool n'ajoute rien de
        # dangereux dans `context_for_llm`).
        result = _run(
            _ctx(),
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
            transactions={"orders_count": 5},
        )
        ctx_keys = set(result["context_for_llm"].keys())
        # Liste positive autorisée (alignée avec la spec § 2.3).
        allowed_keys = {
            "kyc_complete",
            "kyc_status",
            "account_state",
            "registration_completed_steps",
            "registration_total_steps",
            "documents_total",
            "documents_by_status",
            "orders_count",
            "first_deposit_done",
        }
        # Aucun champ inattendu (= signal interne aurait fuité).
        assert ctx_keys.issubset(allowed_keys)
        # Pas de "risk_score", "level", "deny_reason"…
        assert "risk_score" not in result["context_for_llm"]
        assert "level" not in result["context_for_llm"]


# ─────────────────────────────────────────────────────────────────────────
# G. Robustesse — repo errors
# ─────────────────────────────────────────────────────────────────────────


class TestRobustness:
    def test_repo_exception_swallowed(self):
        from services.assistance.agents.tools.compliance import (
            diagnose_compliance_topic as mod,
        )

        with patch.object(
            mod.compliance_repo,
            "fetch_compliance_state_snapshot",
            side_effect=RuntimeError("db down"),
        ), patch.object(
            mod.compliance_repo,
            "fetch_registration_progress",
            return_value={},
        ), patch.object(
            mod.compliance_repo,
            "fetch_documents_summary",
            return_value={},
        ), patch.object(
            mod.compliance_repo,
            "fetch_transactions_summary",
            return_value={},
        ):
            result = diagnose_compliance_topic.execute(
                _ctx(), user_message_hint="bonjour"
            )
        # Pas d'exception → fallback general avec 0 trigger utile.
        assert result["dominant_topic"] == "general"
        assert "no_specific_signal" in result["triggers_used"]

    def test_user_hint_truncated_at_500(self):
        # Pas d'erreur si on envoie un hint très long.
        result = _run(
            _ctx(),
            hint="x" * 5000,
            status={"kyc_status": "approved", "account_state": "ACTIVE"},
        )
        # Pas d'assertion forte sur le topic, juste pas de plantage.
        assert "dominant_topic" in result


# ─────────────────────────────────────────────────────────────────────────
# H. SPEC du tool
# ─────────────────────────────────────────────────────────────────────────


class TestToolSpec:
    def test_spec_metadata(self):
        spec = diagnose_compliance_topic.SPEC
        assert spec["function"]["name"] == "diagnose_compliance_topic"
        assert spec["autonomy_level"] == "L0"
        assert spec["agent_id"] == "compliance"
        # Le param `user_message_hint` est optionnel mais documenté.
        params = spec["function"]["parameters"]
        assert "user_message_hint" in params["properties"]
        assert params["additionalProperties"] is False
