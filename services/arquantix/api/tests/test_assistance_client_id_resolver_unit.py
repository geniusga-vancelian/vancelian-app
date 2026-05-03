"""Tests unitaires de `services.auth.client_id_resolver` — Phase 2a.

Couvre la promotion globale du fix BUG B (cf. `AUDIT_AUTH_IDENTITIES.md`
§ 7, décision 4).

Ce helper est volontairement stateless et fail-safe : les tests doivent
garantir qu'**aucun** chemin d'erreur ne lève d'exception.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID, uuid4

from services.auth.client_id_resolver import patch_auth_client_id_from_person
from services.auth.models import AuthContext


def _make_auth(
    *,
    user_id: int = 42,
    person_id: UUID | None = None,
    client_id: UUID | None = None,
) -> AuthContext:
    return AuthContext(
        user_id=user_id,
        email=None,
        role="admin",
        zero_trust_role="admin",
        person_id=person_id,
        client_id=client_id,
        jwt_sub_typ="user_id",
    )


class TestPatchAuthClientId:
    def test_no_op_when_client_id_already_set(self):
        cid = uuid4()
        auth = _make_auth(client_id=cid, person_id=uuid4())
        db = MagicMock()
        # db ne doit JAMAIS être touché si client_id déjà résolu
        result = patch_auth_client_id_from_person(auth, db)
        assert result is True
        assert auth.client_id == cid
        db.query.assert_not_called()

    def test_returns_false_when_no_person_id(self):
        auth = _make_auth(client_id=None, person_id=None)
        db = MagicMock()
        result = patch_auth_client_id_from_person(auth, db)
        assert result is False
        assert auth.client_id is None
        db.query.assert_not_called()

    def test_patches_client_id_when_lookup_succeeds(self):
        target = uuid4()
        person = uuid4()
        auth = _make_auth(client_id=None, person_id=person)
        db = MagicMock()
        db.query.return_value.filter.return_value.one_or_none.return_value = (
            target,
        )
        result = patch_auth_client_id_from_person(auth, db)
        assert result is True
        assert auth.client_id == target

    def test_returns_false_when_no_pe_client_row(self):
        person = uuid4()
        auth = _make_auth(client_id=None, person_id=person)
        db = MagicMock()
        db.query.return_value.filter.return_value.one_or_none.return_value = None
        result = patch_auth_client_id_from_person(auth, db)
        assert result is False
        assert auth.client_id is None

    def test_db_error_returns_false_no_exception(self):
        person = uuid4()
        auth = _make_auth(client_id=None, person_id=person)
        db = MagicMock()
        db.query.side_effect = RuntimeError("db down")
        result = patch_auth_client_id_from_person(auth, db)
        assert result is False
        assert auth.client_id is None

    def test_idempotent_calls(self):
        target = uuid4()
        person = uuid4()
        auth = _make_auth(client_id=None, person_id=person)
        db = MagicMock()
        db.query.return_value.filter.return_value.one_or_none.return_value = (
            target,
        )
        # Premier appel : patch
        patch_auth_client_id_from_person(auth, db)
        # Deuxième appel : no-op
        result = patch_auth_client_id_from_person(auth, db)
        assert result is True
        # db.query a été appelé une seule fois (pas re-query au 2e appel)
        assert db.query.call_count == 1
