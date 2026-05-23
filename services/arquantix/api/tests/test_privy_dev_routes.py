"""Tests endpoints dev ``/auth/privy/dev-*`` (liaison Person sans SQL manuel)."""
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
    reason="Appliquer `alembic upgrade head` (156) pour les tests Privy dev routes.",
)


def test_privy_dev_link_forbidden_when_not_allowed(client: TestClient, monkeypatch):
    from services.auth import privy_dev_tools

    monkeypatch.setattr(
        privy_dev_tools,
        "privy_dev_tools_allowed",
        lambda _request: False,
    )
    res = client.post(
        "/auth/privy/dev-link",
        json={
            "person_id": str(uuid.uuid4()),
            "privy_user_id": "did:privy:test",
        },
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "privy.dev_link_forbidden"


def test_privy_dev_current_person_forbidden_when_not_allowed(
    client: TestClient, monkeypatch,
):
    from services.auth import privy_dev_tools

    monkeypatch.setattr(
        privy_dev_tools,
        "privy_dev_tools_allowed",
        lambda _request: False,
    )
    res = client.get("/auth/privy/dev-current-person")
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "privy.dev_link_forbidden"


def test_privy_dev_link_creates_identity(client: TestClient, db: Session):
    c = make_linked_client(db)
    ext = f"did:privy:e2e-{uuid.uuid4().hex[:12]}"
    res = client.post(
        "/auth/privy/dev-link",
        json={
            "person_id": str(c.person_id),
            "privy_user_id": ext,
            "email": "privy-dev@example.com",
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


def test_privy_dev_link_idempotent(client: TestClient, db: Session):
    c = make_linked_client(db)
    ext = f"did:privy:idem-{uuid.uuid4().hex[:10]}"
    r1 = client.post(
        "/auth/privy/dev-link",
        json={"person_id": str(c.person_id), "privy_user_id": ext},
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/auth/privy/dev-link",
        json={
            "person_id": str(c.person_id),
            "privy_user_id": ext,
            "email": "updated@example.com",
        },
    )
    assert r2.status_code == 200, r2.text
    assert r2.json().get("idempotent") is True


def test_privy_dev_link_conflict_other_person(client: TestClient, db: Session):
    c1 = make_linked_client(db)
    c2 = make_linked_client(db)
    ext = f"did:privy:conflict-{uuid.uuid4().hex[:10]}"
    r1 = client.post(
        "/auth/privy/dev-link",
        json={"person_id": str(c1.person_id), "privy_user_id": ext},
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/auth/privy/dev-link",
        json={"person_id": str(c2.person_id), "privy_user_id": ext},
    )
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "privy.dev_link_conflict"


def test_privy_dev_current_person_requires_session(client: TestClient):
    res = client.get("/auth/privy/dev-current-person")
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "privy.dev_current_person_requires_session"


def test_privy_dev_current_person_with_jwt(client: TestClient, db: Session):
    c = make_linked_client(db)
    u = ensure_admin_for_linked_client(db, c)
    db.commit()
    token = create_access_token(build_user_jwt_access_base_claims(u))
    res = client.get(
        "/auth/privy/dev-current-person",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["person_id"] == str(c.person_id)
    assert body["pe_client_id"] == str(c.id)
    assert str(body.get("jwt_subject") or "").startswith("au:")
