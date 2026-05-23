"""Tests ``POST /auth/privy/link`` (liaison Privy sous JWT Vancelian)."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from services.auth.person_identity_bridge import PROVIDER_PRIVY, get_person_from_external_identity
from tests.conftest import ensure_admin_for_linked_client, make_linked_client
from tests.test_person_identity_bridge import _migration_156_applied


pytestmark = pytest.mark.skipif(
    not _migration_156_applied(),
    reason="Appliquer `alembic upgrade head` (156) pour les tests Privy link routes.",
)


def test_privy_link_requires_session(client: TestClient):
    res = client.post(
        "/auth/privy/link",
        json={"privy_user_id": "did:privy:test-no-auth"},
    )
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "privy.link_requires_session"


def test_privy_link_creates_identity(client: TestClient, db: Session):
    c = make_linked_client(db)
    u = ensure_admin_for_linked_client(db, c)
    db.commit()
    token = create_access_token(build_user_jwt_access_base_claims(u))
    ext = f"did:privy:link-{uuid.uuid4().hex[:12]}"
    res = client.post(
        "/auth/privy/link",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "privy_user_id": ext,
            "email": "privy-link@example.com",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("ok") is True
    assert body.get("idempotent") is False
    db.commit()
    p = get_person_from_external_identity(
        db, provider=PROVIDER_PRIVY, external_subject=ext
    )
    assert p is not None
    assert p.id == c.person_id


def test_privy_link_idempotent(client: TestClient, db: Session):
    c = make_linked_client(db)
    u = ensure_admin_for_linked_client(db, c)
    db.commit()
    token = create_access_token(build_user_jwt_access_base_claims(u))
    ext = f"did:privy:link-idem-{uuid.uuid4().hex[:10]}"
    r1 = client.post(
        "/auth/privy/link",
        headers={"Authorization": f"Bearer {token}"},
        json={"privy_user_id": ext},
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/auth/privy/link",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "privy_user_id": ext,
            "email": "updated-link@example.com",
        },
    )
    assert r2.status_code == 200, r2.text
    assert r2.json().get("idempotent") is True


def test_privy_link_conflict_other_person(client: TestClient, db: Session):
    c1 = make_linked_client(db)
    u1 = ensure_admin_for_linked_client(db, c1)
    c2 = make_linked_client(db)
    u2 = ensure_admin_for_linked_client(db, c2)
    db.commit()
    ext = f"did:privy:link-conf-{uuid.uuid4().hex[:10]}"
    t1 = create_access_token(build_user_jwt_access_base_claims(u1))
    r1 = client.post(
        "/auth/privy/link",
        headers={"Authorization": f"Bearer {t1}"},
        json={"privy_user_id": ext},
    )
    assert r1.status_code == 200

    t2 = create_access_token(build_user_jwt_access_base_claims(u2))
    r2 = client.post(
        "/auth/privy/link",
        headers={"Authorization": f"Bearer {t2}"},
        json={"privy_user_id": ext},
    )
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "privy.link_conflict"
