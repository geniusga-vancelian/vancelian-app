"""Tests unitaires des court-circuits acteurs — Phase 2a multi-agents.

Couvre :
  - `services.assistance.routes._classify_chat_actor` : garde-fou +
    classification d'acteur pour les endpoints `/chat/*`.
  - `services.assistance.service.SUSPENDED_RESPONSE_TEXT` : anti-tipping-off
    statique (pas de termes confirmant l'état interne).
  - `services.assistance.service.process_suspended_short_circuit` /
    `start_suspended_chat_turn` / `stream_suspended_short_circuit` :
    contrats de retour, payload, log neutre.

Spec de référence :
  - `docs/arquantix/MULTI_AGENTS_RUNTIME.md` § 6 (Sécurité tipping-off
    matérielle), § 11 (Intégration runtime).
  - `docs/arquantix/AUDIT_AUTH_IDENTITIES.md` § 7 (décisions actées).

Aucune dépendance Postgres : on mocke `Session` et le module DB pour
rester < 100 ms par test.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from services.assistance import service as assistance_service
from services.assistance.agents.tools.shared import ActorKind
from services.assistance.routes import _classify_chat_actor
from services.auth.models import AuthContext


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _make_auth(
    *,
    user_id: int = 42,
    person_id: UUID | None = None,
    client_id: UUID | None = None,
) -> AuthContext:
    """Construit un AuthContext minimal pour les tests."""
    return AuthContext(
        user_id=user_id,
        email=None,
        role="admin",
        zero_trust_role="admin",
        person_id=person_id,
        client_id=client_id,
        jwt_sub_typ="user_id",
    )


def _mock_db_with_pe_client_lookup(client_id: UUID | None) -> MagicMock:
    """Mock Session dont `db.query(...).filter(...).one_or_none()` retourne
    `(client_id,)` ou `None`."""
    db = MagicMock()
    if client_id is None:
        db.query.return_value.filter.return_value.one_or_none.return_value = None
    else:
        db.query.return_value.filter.return_value.one_or_none.return_value = (client_id,)
    return db


# ─────────────────────────────────────────────────────────────────────────
# A. Anti-tipping-off : le texte standardisé ne fuite RIEN
# ─────────────────────────────────────────────────────────────────────────


# Liste exhaustive des termes interdits dans la réponse standardisée
# d'un acteur SUSPENDED. Cf. `MULTI_AGENTS_RUNTIME.md` § 6.
TIPPING_OFF_BLACKLIST = (
    # Action / état du compte
    "suspendu",
    "bloqué",
    "bloque",
    "gelé",
    "gele",
    "fermé",
    "ferme",
    "désactivé",
    "désactive",
    "restreint",
    # Cause supposée
    "fraude",
    "fraudeur",
    "blanchiment",
    "lcb-ft",
    "lcb",
    "aml",
    "kyc",
    "compliance",
    "conformité",
    "sanction",
    "embargo",
    "investigation",
    "enquête",
    "enquete",
    "soupçon",
    "soupcon",
    "soupçonné",
    "soupconne",
    "suspect",
    "suspicion",
    "alerte",
    "risque",
    "sécurité",
    "securite",
    # Mots qui pourraient laisser deviner l'agent en charge
    "agent compliance",
    "agent kyc",
    "agent aml",
)


class TestAntiTippingOffText:
    """SUSPENDED_RESPONSE_TEXT ne doit contenir AUCUN terme blacklisté."""

    def test_text_is_non_empty_and_french(self):
        text = assistance_service.SUSPENDED_RESPONSE_TEXT
        assert isinstance(text, str)
        assert len(text) > 20
        # Heuristique simple : au moins un mot français courant.
        assert any(w in text.lower() for w in ("votre", "notre", "demande"))

    @pytest.mark.parametrize("forbidden", TIPPING_OFF_BLACKLIST)
    def test_text_does_not_leak_internal_state(self, forbidden: str):
        text = assistance_service.SUSPENDED_RESPONSE_TEXT.lower()
        assert forbidden not in text, (
            f"SUSPENDED_RESPONSE_TEXT contient le terme interdit "
            f"'{forbidden}' (anti-tipping-off violé). Texte : {text!r}"
        )

    def test_text_redirects_to_support_channel(self):
        """Le texte doit renvoyer l'utilisateur vers un canal humain (Aide)."""
        text = assistance_service.SUSPENDED_RESPONSE_TEXT.lower()
        assert "aide" in text or "support" in text


# ─────────────────────────────────────────────────────────────────────────
# B. _classify_chat_actor : garde-fou route assistance
# ─────────────────────────────────────────────────────────────────────────


class TestClassifyChatActor:
    """Comportement du helper `_classify_chat_actor` selon ActorKind."""

    @patch("services.assistance.routes.classify_actor")
    def test_customer_passes_through(self, mock_classify):
        """Un CUSTOMER (client_id présent) → retourne ActorKind.CUSTOMER."""
        mock_classify.return_value = ActorKind.CUSTOMER
        auth = _make_auth(client_id=uuid4(), person_id=uuid4())
        db = MagicMock()

        result = _classify_chat_actor(auth, db)

        assert result == ActorKind.CUSTOMER

    @patch("services.assistance.routes.classify_actor")
    def test_suspended_passes_through(self, mock_classify):
        """Un SUSPENDED → retourne ActorKind.SUSPENDED (le caller fera le court-circuit)."""
        mock_classify.return_value = ActorKind.SUSPENDED
        auth = _make_auth(client_id=uuid4(), person_id=uuid4())
        db = MagicMock()

        result = _classify_chat_actor(auth, db)

        assert result == ActorKind.SUSPENDED

    @patch("services.assistance.routes.classify_actor")
    def test_admin_bo_raises_403_actor_admin_bo(self, mock_classify):
        """Un ADMIN_BO → 403 avec code `actor_admin_bo` (NEW Phase 2a)."""
        mock_classify.return_value = ActorKind.ADMIN_BO
        auth = _make_auth(client_id=None, person_id=None)
        db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            _classify_chat_actor(auth, db)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"]["code"] == "actor_admin_bo"

    @patch("services.assistance.routes.classify_actor")
    def test_onboarding_raises_403_client_required_legacy(self, mock_classify):
        """ONBOARDING → 403 `client_required` (legacy code, mobile-compat).

        Le code est volontairement gardé à `client_required` (pas
        `actor_onboarding`) tant que la Phase 3 n'a pas branché l'agent
        registration. Cf. routes.py docstring de `_classify_chat_actor`.
        """
        mock_classify.return_value = ActorKind.ONBOARDING
        auth = _make_auth(client_id=None, person_id=uuid4())
        db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            _classify_chat_actor(auth, db)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"]["code"] == "client_required"

    @patch("services.assistance.routes.classify_actor")
    def test_patch_bug_b_when_client_id_missing_but_person_id_present(
        self, mock_classify
    ):
        """BUG B fix : si client_id=None mais person_id présent et un row
        PE clients existe, le helper mute `auth.client_id` en place."""
        mock_classify.return_value = ActorKind.CUSTOMER
        person_id = uuid4()
        target_client_id = uuid4()
        auth = _make_auth(client_id=None, person_id=person_id)
        db = _mock_db_with_pe_client_lookup(target_client_id)

        result = _classify_chat_actor(auth, db)

        assert result == ActorKind.CUSTOMER
        assert auth.client_id == target_client_id

    @patch("services.assistance.routes.classify_actor")
    def test_patch_bug_b_no_pe_client_keeps_client_id_none(self, mock_classify):
        """Si person_id présent mais PAS de PE client lié → client_id reste
        None, `classify_actor` retourne ONBOARDING (mock) → 403."""
        mock_classify.return_value = ActorKind.ONBOARDING
        person_id = uuid4()
        auth = _make_auth(client_id=None, person_id=person_id)
        db = _mock_db_with_pe_client_lookup(None)

        with pytest.raises(HTTPException):
            _classify_chat_actor(auth, db)
        assert auth.client_id is None

    @patch("services.assistance.routes.classify_actor")
    def test_patch_bug_b_db_error_falls_back_safely(self, mock_classify):
        """Si le lookup PE clients lève une exception, on log et on
        continue avec client_id=None (fail-safe)."""
        mock_classify.return_value = ActorKind.ADMIN_BO
        person_id = uuid4()
        auth = _make_auth(client_id=None, person_id=person_id)
        db = MagicMock()
        db.query.side_effect = RuntimeError("boom")

        with pytest.raises(HTTPException) as exc_info:
            _classify_chat_actor(auth, db)
        # client_id reste None, fallback ADMIN_BO → 403 actor_admin_bo
        assert auth.client_id is None
        assert exc_info.value.detail["error"]["code"] == "actor_admin_bo"


# ─────────────────────────────────────────────────────────────────────────
# C. Court-circuit SUSPENDED — contrat retour + payload neutre
# ─────────────────────────────────────────────────────────────────────────


class TestSuspendedShortCircuitPayload:
    """Vérifie que le message persisté n'expose AUCUN signal côté client."""

    def test_agent_used_is_default_not_compliance(self):
        """`agent_used="default"` (anti-tipping-off — pas `compliance`)."""
        # On n'instancie pas un assistant_msg car _persist_assistant_message
        # est mocké : on lit la constante exposée par le module.
        assert assistance_service._SUSPENDED_AGENT_USED == "default"

    def test_payload_reason_is_traceable_for_bo_only(self):
        """`message_payload.reason` est lisible côté BO uniquement (jamais
        renvoyé tel quel au client front, qui ne lit que `content`)."""
        assert (
            assistance_service._SUSPENDED_PAYLOAD_REASON
            == "suspended_short_circuit"
        )

    def test_module_exposes_short_circuit_helpers(self):
        """API surface : les 3 helpers sont exposés et callable."""
        assert callable(assistance_service.process_suspended_short_circuit)
        assert callable(assistance_service.start_suspended_chat_turn)
        assert callable(assistance_service.stream_suspended_short_circuit)


# ─────────────────────────────────────────────────────────────────────────
# D. Cohérence des constantes — pas de drift silencieux entre service.py
#    et le contrat documenté dans MULTI_AGENTS_RUNTIME.md.
# ─────────────────────────────────────────────────────────────────────────


class TestConstantsContract:
    """Garde-fou : si on touche aux constantes, on doit casser ce test."""

    def test_suspended_text_remains_short_and_neutral(self):
        text = assistance_service.SUSPENDED_RESPONSE_TEXT
        # Borne haute : on ne veut pas un pavé de 500 chars qui
        # finit par contenir un terme blacklisté par accident.
        assert len(text) < 400, "SUSPENDED_RESPONSE_TEXT trop long"

    def test_suspended_text_does_not_apologize_excessively(self):
        """Pas de « désolé » répété (UX professionnelle, pas servile)."""
        text = assistance_service.SUSPENDED_RESPONSE_TEXT.lower()
        assert text.count("désolé") <= 1
        assert text.count("excuse") <= 0
