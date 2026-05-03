"""Tests unitaires de `classify_actor()` — Phase 2a multi-agents.

Couvre la primitive de classification d'acteur définie dans
`services/assistance/agents/tools/shared/classify_actor.py`.

Spec de référence :
  - `docs/arquantix/AUDIT_AUTH_IDENTITIES.md` § 7.1
  - `docs/arquantix/MULTI_AGENTS_RUNTIME.md` § 11

Conventions :
  - Pas de DB réelle : on mock la session SQLAlchemy via
    `unittest.mock.MagicMock` configuré pour retourner les rows
    `(login_frozen, account_state)` voulus.
  - `AuthContext` instancié directement (Pydantic v2, pas de validation
    réseau / JWT).
  - Une assertion par test, grouping par classe = catégorie d'acteur.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from services.assistance.agents.tools.shared.classify_actor import (
    ActorKind,
    classify_actor,
)
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
        role="admin",  # hardcodé partout dans le code (cf. AUDIT § 5.1)
        zero_trust_role="admin",
        person_id=person_id,
        client_id=client_id,
        jwt_sub_typ="user_id",
    )


def _make_db_returning(login_frozen: bool, account_state: str | None) -> MagicMock:
    """Mock de Session qui retourne un row (login_frozen, account_state)."""
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = (
        (login_frozen, account_state)
    )
    return db


def _make_db_returning_no_person() -> MagicMock:
    """Mock de Session qui retourne None (pas de personne trouvée)."""
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None
    return db


def _make_db_raising() -> MagicMock:
    """Mock de Session qui lève une exception au query (test fail-safe)."""
    db = MagicMock()
    db.query.side_effect = RuntimeError("simulated DB outage")
    return db


# ─────────────────────────────────────────────────────────────────────────
# CUSTOMER — chemin nominal
# ─────────────────────────────────────────────────────────────────────────


class TestCustomer:
    """auth.client_id résolu + person non gelée → CUSTOMER."""

    def test_classifies_customer_when_client_id_present_and_not_frozen(self):
        person_id = uuid4()
        client_id = uuid4()
        auth = _make_auth(person_id=person_id, client_id=client_id)
        db = _make_db_returning(login_frozen=False, account_state="ACTIVE")

        kind = classify_actor(auth, db)

        assert kind == ActorKind.CUSTOMER

    def test_classifies_customer_when_account_state_is_none(self):
        """`account_state IS NULL` n'est pas dans la liste suspended."""
        auth = _make_auth(person_id=uuid4(), client_id=uuid4())
        db = _make_db_returning(login_frozen=False, account_state=None)

        kind = classify_actor(auth, db)

        assert kind == ActorKind.CUSTOMER


# ─────────────────────────────────────────────────────────────────────────
# ONBOARDING — person sans pe_clients
# ─────────────────────────────────────────────────────────────────────────


class TestOnboarding:
    """auth.person_id présent, auth.client_id None → ONBOARDING."""

    def test_classifies_onboarding_when_person_but_no_client(self):
        auth = _make_auth(person_id=uuid4(), client_id=None)
        db = _make_db_returning(login_frozen=False, account_state="ACTIVE")

        kind = classify_actor(auth, db)

        assert kind == ActorKind.ONBOARDING

    def test_classifies_onboarding_when_person_exists_but_no_account_state(self):
        auth = _make_auth(person_id=uuid4(), client_id=None)
        db = _make_db_returning(login_frozen=False, account_state=None)

        kind = classify_actor(auth, db)

        assert kind == ActorKind.ONBOARDING


# ─────────────────────────────────────────────────────────────────────────
# ADMIN_BO — pas de person_id ni client_id
# ─────────────────────────────────────────────────────────────────────────


class TestAdminBO:
    """admin pur (admin_users.person_id IS NULL) → ADMIN_BO."""

    def test_classifies_admin_bo_when_no_person_id_no_client_id(self):
        auth = _make_auth(person_id=None, client_id=None)
        db = MagicMock()  # ne devrait pas être interrogée

        kind = classify_actor(auth, db)

        assert kind == ActorKind.ADMIN_BO

    def test_no_db_query_when_no_person_id(self):
        """Quand person_id est None, on ne touche pas à la DB."""
        auth = _make_auth(person_id=None, client_id=None)
        db = MagicMock()

        classify_actor(auth, db)

        db.query.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────
# SUSPENDED — priorité absolue
# ─────────────────────────────────────────────────────────────────────────


class TestSuspended:
    """SUSPENDED prime sur tout (login_frozen OU account_state à risque)."""

    def test_classifies_suspended_when_login_frozen_true(self):
        """Même un CUSTOMER (client_id présent) bascule en SUSPENDED."""
        auth = _make_auth(person_id=uuid4(), client_id=uuid4())
        db = _make_db_returning(login_frozen=True, account_state="ACTIVE")

        kind = classify_actor(auth, db)

        assert kind == ActorKind.SUSPENDED

    def test_classifies_suspended_when_account_state_partial(self):
        auth = _make_auth(person_id=uuid4(), client_id=uuid4())
        db = _make_db_returning(login_frozen=False, account_state="PARTIAL")

        kind = classify_actor(auth, db)

        assert kind == ActorKind.SUSPENDED

    def test_classifies_suspended_when_account_state_blocked(self):
        auth = _make_auth(person_id=uuid4(), client_id=uuid4())
        db = _make_db_returning(login_frozen=False, account_state="BLOCKED")

        kind = classify_actor(auth, db)

        assert kind == ActorKind.SUSPENDED

    def test_suspended_priority_over_onboarding(self):
        """ONBOARDING (person sans client) gelé → SUSPENDED."""
        auth = _make_auth(person_id=uuid4(), client_id=None)
        db = _make_db_returning(login_frozen=True, account_state=None)

        kind = classify_actor(auth, db)

        assert kind == ActorKind.SUSPENDED


# ─────────────────────────────────────────────────────────────────────────
# Robustesse — fail-safe sur erreur DB et person introuvable
# ─────────────────────────────────────────────────────────────────────────


class TestRobustness:
    """Comportement en cas d'anomalie."""

    def test_db_error_returns_customer_when_client_id_present(self):
        """Si la DB plante mais client_id est résolu, on tombe en CUSTOMER
        (le check SUSPENDED n'a pas pu confirmer le gel mais l'auth a
        validé le client_id en amont)."""
        auth = _make_auth(person_id=uuid4(), client_id=uuid4())
        db = _make_db_raising()

        kind = classify_actor(auth, db)

        assert kind == ActorKind.CUSTOMER

    def test_person_not_found_returns_customer_when_client_id_present(self):
        """Si la `persons` row n'existe pas (cas anormal mais possible
        en cas de cache désynchronisé), on retombe sur la classification
        normale (ici CUSTOMER vu client_id)."""
        auth = _make_auth(person_id=uuid4(), client_id=uuid4())
        db = _make_db_returning_no_person()

        kind = classify_actor(auth, db)

        assert kind == ActorKind.CUSTOMER

    def test_db_error_with_no_client_returns_onboarding(self):
        """Si DB plante et qu'on n'a que le person_id, on tombe en
        ONBOARDING (pas SUSPENDED par défaut, pour ne pas bloquer un
        client en cours d'inscription par accident DB)."""
        auth = _make_auth(person_id=uuid4(), client_id=None)
        db = _make_db_raising()

        kind = classify_actor(auth, db)

        assert kind == ActorKind.ONBOARDING


# ─────────────────────────────────────────────────────────────────────────
# Sérialisation — ActorKind hérite de str
# ─────────────────────────────────────────────────────────────────────────


class TestActorKindEnum:
    """ActorKind est un StrEnum-like (hérite de str)."""

    def test_actor_kind_value_is_lowercase_string(self):
        assert ActorKind.CUSTOMER.value == "customer"
        assert ActorKind.ONBOARDING.value == "onboarding"
        assert ActorKind.ADMIN_BO.value == "admin_bo"
        assert ActorKind.SUSPENDED.value == "suspended"

    def test_actor_kind_is_str_compatible(self):
        """Permet une comparaison directe `actor == 'customer'`."""
        assert ActorKind.CUSTOMER == "customer"
        assert "suspended" == ActorKind.SUSPENDED

    def test_actor_kind_json_serializable(self):
        """Pour pouvoir sérialiser dans `agent_decisions.result_summary`."""
        import json

        encoded = json.dumps({"actor": ActorKind.CUSTOMER.value})
        assert encoded == '{"actor": "customer"}'


# ─────────────────────────────────────────────────────────────────────────
# Idempotence et 0 side-effect
# ─────────────────────────────────────────────────────────────────────────


class TestIdempotence:
    """classify_actor n'écrit jamais en DB."""

    def test_no_commit_called(self):
        auth = _make_auth(person_id=uuid4(), client_id=uuid4())
        db = _make_db_returning(login_frozen=False, account_state=None)

        classify_actor(auth, db)

        db.commit.assert_not_called()
        db.flush.assert_not_called()
        db.add.assert_not_called()

    def test_calling_twice_returns_same_result(self):
        auth = _make_auth(person_id=uuid4(), client_id=uuid4())
        db = _make_db_returning(login_frozen=False, account_state=None)

        first = classify_actor(auth, db)
        second = classify_actor(auth, db)

        assert first == second == ActorKind.CUSTOMER
