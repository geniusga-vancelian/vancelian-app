"""Modèle V1 security_preferences : migration, dérivation, validation, PATCH."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from conftest import ensure_admin_for_linked_client, make_linked_client
from database import Person
from sqlalchemy.orm.attributes import flag_modified
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from services.test_clients.security_preferences_v1 import (
    build_security_preferences_read_dict,
    derive_legacy_flat,
    merge_patch_into_security,
    migrate_legacy_to_v1,
)


def test_migrate_legacy_only_to_v1_structure():
    sec = {
        "biometric_unlock_enabled": True,
        "biometric_login_onboarding_completed": True,
        "push_notifications_enabled": False,
        "push_notifications_onboarding_completed": True,
    }
    v1 = migrate_legacy_to_v1(sec)
    assert v1["security_model_version"] == 1
    assert v1["biometric"]["onboarding_status"] == "completed"
    assert v1["biometric"]["onboarding_outcome"] == "enabled"
    assert v1["push_notifications"]["onboarding_outcome"] == "skipped"
    assert v1["biometric_unlock_enabled"] is True
    assert v1["push_notifications_enabled"] is False


def test_derive_legacy_flat_strict():
    bio = {
        "preference_enabled": True,
        "onboarding_status": "completed",
    }
    push = {"preference_enabled": False, "onboarding_status": "completed"}
    d = derive_legacy_flat(bio, push)
    assert d["biometric_unlock_enabled"] is True
    assert d["biometric_login_onboarding_completed"] is True
    assert d["push_notifications_enabled"] is False
    assert d["push_notifications_onboarding_completed"] is True


def test_merge_patch_sets_completed_and_derives_legacy():
    sec0: dict = {}
    out = merge_patch_into_security(
        sec0,
        {
            "preference_enabled": True,
            "onboarding_outcome": "enabled",
            "onboarding_source": "app_ios",
            "device_capability_last_known": "available",
        },
        {"preference_enabled": False, "onboarding_outcome": "skipped"},
    )
    assert out["biometric"]["onboarding_status"] == "completed"
    assert out["biometric"]["onboarding_completed_at"] is not None
    assert out["biometric_unlock_enabled"] is True
    assert out["push_notifications"]["onboarding_status"] == "completed"
    assert out["push_notifications_enabled"] is False


def test_reject_biometric_unavailable_with_capability_available():
    with pytest.raises(ValueError, match="incompatible"):
        merge_patch_into_security(
            {},
            {"onboarding_outcome": "unavailable", "device_capability_last_known": "available"},
            None,
        )


def test_patch_security_preferences_endpoint(client: TestClient, db: Session):
    c = make_linked_client(db)
    u = ensure_admin_for_linked_client(db, c)
    token = create_access_token(build_user_jwt_access_base_claims(u))
    res = client.patch(
        "/api/mobile/flutter/profile/security-preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "biometric": {
                "preference_enabled": True,
                "onboarding_outcome": "enabled",
                "onboarding_source": "app_ios",
                "device_capability_last_known": "available",
            }
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["security_model_version"] == 1
    assert body["biometric"]["onboarding_status"] == "completed"
    assert body["biometric_unlock_enabled"] is True
    assert body["biometric_login_onboarding_completed"] is True

    res2 = client.get(
        "/api/mobile/flutter/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    sp = res2.json()["security_preferences"]
    assert sp["biometric"]["onboarding_status"] == "completed"
    assert sp["biometric_unlock_enabled"] is True


def test_patch_rejects_legacy_flat_fields(client: TestClient, db: Session):
    c = make_linked_client(db)
    u = ensure_admin_for_linked_client(db, c)
    token = create_access_token(build_user_jwt_access_base_claims(u))
    res = client.patch(
        "/api/mobile/flutter/profile/security-preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"biometric_unlock_enabled": True},
    )
    assert res.status_code == 422


def test_get_profile_includes_structured_security_preferences(
    client: TestClient, db: Session,
):
    c = make_linked_client(db)
    person = db.query(Person).filter(Person.id == c.person_id).first()
    pj = dict(person.profile_json or {})
    sec = dict(pj.get("security") or {})
    sec.update(
        {
            "biometric_unlock_enabled": True,
            "biometric_login_onboarding_completed": True,
            "push_notifications_enabled": False,
            "push_notifications_onboarding_completed": False,
        }
    )
    pj["security"] = sec
    person.profile_json = pj
    flag_modified(person, "profile_json")
    db.commit()

    u = ensure_admin_for_linked_client(db, c)
    token = create_access_token(build_user_jwt_access_base_claims(u))
    res = client.get(
        "/api/mobile/flutter/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    sp = res.json()["security_preferences"]
    assert "security_model_version" in sp
    assert "biometric" in sp
    assert "push_notifications" in sp
    assert sp["biometric_unlock_enabled"] is True


def test_build_read_dict_empty():
    d = build_security_preferences_read_dict({})
    assert d["security_model_version"] == 1
    assert d["biometric"]["onboarding_status"] == "not_started"
