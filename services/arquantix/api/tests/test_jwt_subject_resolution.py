"""Tests résolution JWT : ``sub`` = ``au:<admin_users.id>`` uniquement."""
from __future__ import annotations

import uuid

import pytest
from jose import jwt

from auth import ALGORITHM, SECRET_KEY, create_access_token, create_registration_otp_token, get_password_hash
from database import AdminUser
from services.auth.jwt_subject_resolution import (
    NonUserJWTSubjectError,
    classify_sub_format,
    get_jwt_sub_resolution_metrics,
    is_non_user_subject_token,
    reset_jwt_sub_resolution_metrics,
    resolve_user_from_jwt_sub,
)
from services.auth.jwt_user_claims import format_user_jwt_sub


@pytest.fixture(autouse=True)
def _reset_metrics():
    reset_jwt_sub_resolution_metrics()
    yield
    reset_jwt_sub_resolution_metrics()


def test_resolve_by_au_prefix(db):
    u = AdminUser(
        email=f"au-user-{uuid.uuid4().hex}@example.com",
        hashed_password=get_password_hash("x"),
    )
    db.add(u)
    db.flush()
    uid = u.id

    user, sub_typ, kind = resolve_user_from_jwt_sub(db, f"au:{uid}")
    assert kind == "ok"
    assert sub_typ == "user_id"
    assert user is not None and user.id == uid


def test_plain_numeric_sub_invalid(db):
    u = AdminUser(email=f"n-{uuid.uuid4().hex}@example.com", hashed_password=get_password_hash("x"))
    db.add(u)
    db.flush()
    user, sub_typ, kind = resolve_user_from_jwt_sub(db, str(u.id))
    assert kind == "invalid"
    assert user is None


def test_au_prefix_non_numeric_invalid(db):
    user, sub_typ, kind = resolve_user_from_jwt_sub(db, "au:abc")
    assert kind == "invalid"
    assert user is None


def test_email_sub_invalid(db):
    email = "legacy-jwt-sub@example.com"
    u = AdminUser(email=email, hashed_password=get_password_hash("x"))
    db.add(u)
    db.flush()

    user, sub_typ, kind = resolve_user_from_jwt_sub(db, email)
    assert kind == "invalid"
    assert user is None


def test_resolve_invalid_sub(db):
    user, sub_typ, kind = resolve_user_from_jwt_sub(db, "not-an-email-or-id")
    assert user is None
    assert kind == "invalid"


def test_registration_raises_by_default(db):
    with pytest.raises(NonUserJWTSubjectError):
        resolve_user_from_jwt_sub(db, "registration:2fa")


def test_registration_allow_non_user_returns_tuple(db):
    user, sub_typ, kind = resolve_user_from_jwt_sub(db, "registration:2fa", allow_non_user_subject=True)
    assert user is None
    assert kind == "non_user"
    assert sub_typ == "registration_special"


def test_is_non_user_subject_token():
    assert is_non_user_subject_token("registration:2fa") is True
    assert is_non_user_subject_token("user@example.com") is False


def test_metrics_increment_on_au_sub(db):
    reset_jwt_sub_resolution_metrics()
    u = AdminUser(email=f"m-{uuid.uuid4().hex}@example.com", hashed_password=get_password_hash("x"))
    db.add(u)
    db.flush()

    resolve_user_from_jwt_sub(db, format_user_jwt_sub(u.id), record_metric=True)
    m = get_jwt_sub_resolution_metrics()
    assert m["jwt_sub_user_id_count"] == 1


def test_access_token_sub_au_roundtrip(db):
    u = AdminUser(email="roundtrip@example.com", hashed_password=get_password_hash("x"))
    db.add(u)
    db.flush()

    token = create_access_token({"sub": format_user_jwt_sub(u.id), "sub_typ": "user_id"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user, sub_typ, kind = resolve_user_from_jwt_sub(db, str(payload["sub"]))
    assert kind == "ok"
    assert sub_typ == "user_id"
    assert user.id == u.id


def test_registration_token_payload_raises(db):
    tok = create_registration_otp_token(__import__("uuid").uuid4())
    payload = jwt.decode(tok, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload.get("sub") == "registration:2fa"
    with pytest.raises(NonUserJWTSubjectError):
        resolve_user_from_jwt_sub(db, str(payload["sub"]))


def test_classify_sub_format():
    assert classify_sub_format("au:42") == "au"
    assert classify_sub_format("42") == "other"
