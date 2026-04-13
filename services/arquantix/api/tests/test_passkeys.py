"""Passkeys / WebAuthn — challenges, credentials, sessions Phase 2, événements."""
from __future__ import annotations

import uuid
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from webauthn.helpers.structs import (
    AttestationFormat,
    CredentialDeviceType,
    PublicKeyCredentialType,
)
from webauthn.registration.verify_registration_response import VerifiedRegistration

from auth import get_password_hash
from database import (
    AdminUser,
    AuthPasskey,
    AuthSession,
    AuthWebAuthnChallenge,
    get_db,
)
from services.auth import passkeys_service
from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests
from services.auth.refresh_session import _utcnow


@pytest.fixture(autouse=True)
def _reset_rl():
    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


@pytest.fixture(autouse=True)
def _relax_passkey_step_up_guard(monkeypatch):
    """Sans OTP complet, le JWT peut porter ``step_up_otp`` ; on neutralise ce garde-fou pour ces tests."""
    monkeypatch.setattr("auth.enforce_access_security", lambda token, user, db: None)


@pytest.fixture
def client_passkeys_db(db):
    """Même instance ``main.app`` que les routes ``@app.post`` (hors ``create_app``)."""
    from main import app

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def _user_token(client: TestClient, db, email: str, password: str) -> str:
    db.add(AdminUser(email=email, hashed_password=get_password_hash(password)))
    db.commit()
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_register_start_creates_challenge(client_passkeys_db, db, monkeypatch):
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "false")
    monkeypatch.setenv("WEBAUTHN_RP_ID", "localhost")
    monkeypatch.setenv("WEBAUTHN_ORIGINS", "http://testserver")
    tok = _user_token(client_passkeys_db, db, "pk_start@example.com", "secret1")
    r = client_passkeys_db.post(
        "/auth/passkeys/register/start",
        json={"device_label": "Pixel"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "options" in data and "challenge_token" in data
    assert db.query(AuthWebAuthnChallenge).filter_by(flow_type="register").count() == 1


def test_register_finish_stores_credential(client_passkeys_db, db, monkeypatch):
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "false")
    monkeypatch.setenv("WEBAUTHN_RP_ID", "localhost")
    monkeypatch.setenv("WEBAUTHN_ORIGINS", "http://testserver")
    tok = _user_token(client_passkeys_db, db, "pk_fin@example.com", "secret2")
    st = client_passkeys_db.post(
        "/auth/passkeys/register/start",
        json={},
        headers={"Authorization": f"Bearer {tok}"},
    )
    challenge_token = st.json()["challenge_token"]

    def _fake_reg(**_kwargs):
        return VerifiedRegistration(
            credential_id=b"unique-cred-id-123",
            credential_public_key=b"\x04" + b"\x00" * 64,
            sign_count=0,
            aaguid="00000000-0000-0000-0000-000000000000",
            fmt=AttestationFormat.NONE,
            credential_type=PublicKeyCredentialType.PUBLIC_KEY,
            user_verified=True,
            attestation_object=b"",
            credential_device_type=CredentialDeviceType.SINGLE_DEVICE,
            credential_backed_up=False,
        )

    monkeypatch.setattr(passkeys_service, "verify_registration_response", _fake_reg)
    r = client_passkeys_db.post(
        "/auth/passkeys/register/finish",
        json={
            "challenge_token": challenge_token,
            "credential": {"id": "x", "rawId": "eA", "response": {}, "type": "public-key"},
            "device_label": "Test",
        },
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    assert db.query(AuthPasskey).count() == 1
    assert db.query(AuthWebAuthnChallenge).count() == 0


def test_login_finish_creates_session(client_passkeys_db, db, monkeypatch):
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "false")
    monkeypatch.setenv("WEBAUTHN_RP_ID", "localhost")
    monkeypatch.setenv("WEBAUTHN_ORIGINS", "http://testserver")
    email = "pk_log@example.com"
    tok = _user_token(client_passkeys_db, db, email, "secret3")
    st = client_passkeys_db.post(
        "/auth/passkeys/register/start",
        json={},
        headers={"Authorization": f"Bearer {tok}"},
    )
    ct = st.json()["challenge_token"]

    def _fake_reg(**_kwargs):
        return VerifiedRegistration(
            credential_id=b"login-cred-xyz",
            credential_public_key=b"\x04" + b"\xab" * 64,
            sign_count=0,
            aaguid="",
            fmt=AttestationFormat.NONE,
            credential_type=PublicKeyCredentialType.PUBLIC_KEY,
            user_verified=True,
            attestation_object=b"",
            credential_device_type=CredentialDeviceType.SINGLE_DEVICE,
            credential_backed_up=False,
        )

    monkeypatch.setattr(passkeys_service, "verify_registration_response", _fake_reg)
    fin = client_passkeys_db.post(
        "/auth/passkeys/register/finish",
        json={
            "challenge_token": ct,
            "credential": {"id": "x", "rawId": "eA", "response": {}, "type": "public-key"},
        },
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert fin.status_code == 200

    from webauthn.authentication.verify_authentication_response import VerifiedAuthentication

    def _fake_auth(**_kwargs):
        return VerifiedAuthentication(
            credential_id=b"login-cred-xyz",
            new_sign_count=7,
            credential_device_type=CredentialDeviceType.SINGLE_DEVICE,
            credential_backed_up=False,
            user_verified=True,
        )

    monkeypatch.setattr(passkeys_service, "verify_authentication_response", _fake_auth)

    lst = client_passkeys_db.post("/auth/passkeys/login/start", json={"email": email})
    assert lst.status_code == 200
    ltok = lst.json()["challenge_token"]
    from webauthn.helpers import bytes_to_base64url

    raw_b64 = bytes_to_base64url(b"login-cred-xyz")
    lf = client_passkeys_db.post(
        "/auth/passkeys/login/finish",
        json={
            "challenge_token": ltok,
            "credential": {
                "id": raw_b64,
                "rawId": raw_b64,
                "response": {"clientDataJSON": "e30", "authenticatorData": "Eg", "signature": "sig"},
                "type": "public-key",
            },
        },
        headers={"X-Device-ID": "passkey-phone"},
    )
    assert lf.status_code == 200, lf.text
    body = lf.json()
    assert body.get("access_token")
    assert body.get("refresh_token")
    assert db.query(AuthSession).filter(AuthSession.device_id == "passkey-phone").count() >= 1
    row = db.query(AuthPasskey).one()
    assert int(row.sign_count) == 7


def test_expired_challenge_rejected(client_passkeys_db, db, monkeypatch):
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "false")
    monkeypatch.setenv("WEBAUTHN_RP_ID", "localhost")
    monkeypatch.setenv("WEBAUTHN_ORIGINS", "http://testserver")
    tok = _user_token(client_passkeys_db, db, "pk_exp@example.com", "secret4")
    st = client_passkeys_db.post(
        "/auth/passkeys/register/start",
        json={},
        headers={"Authorization": f"Bearer {tok}"},
    )
    challenge_token = st.json()["challenge_token"]
    ch = db.query(AuthWebAuthnChallenge).filter_by(id=uuid.UUID(challenge_token)).one()
    ch.expires_at = _utcnow() - timedelta(minutes=5)
    db.commit()

    def _fake_reg(**_kwargs):
        return VerifiedRegistration(
            credential_id=b"x",
            credential_public_key=b"\x04" + b"\x01" * 64,
            sign_count=0,
            aaguid="",
            fmt=AttestationFormat.NONE,
            credential_type=PublicKeyCredentialType.PUBLIC_KEY,
            user_verified=True,
            attestation_object=b"",
            credential_device_type=CredentialDeviceType.SINGLE_DEVICE,
            credential_backed_up=False,
        )

    monkeypatch.setattr(passkeys_service, "verify_registration_response", _fake_reg)
    r = client_passkeys_db.post(
        "/auth/passkeys/register/finish",
        json={
            "challenge_token": challenge_token,
            "credential": {"id": "x", "rawId": "eA", "response": {}, "type": "public-key"},
        },
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 400


def test_revoked_passkey_login_fails(client_passkeys_db, db, monkeypatch):
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "false")
    monkeypatch.setenv("WEBAUTHN_RP_ID", "localhost")
    monkeypatch.setenv("WEBAUTHN_ORIGINS", "http://testserver")
    email = "pk_rev@example.com"
    tok = _user_token(client_passkeys_db, db, email, "secret5")
    st = client_passkeys_db.post(
        "/auth/passkeys/register/start",
        json={},
        headers={"Authorization": f"Bearer {tok}"},
    )
    ct = st.json()["challenge_token"]

    def _fake_reg(**_kwargs):
        return VerifiedRegistration(
            credential_id=b"revoked-cred",
            credential_public_key=b"\x04" + b"\x02" * 64,
            sign_count=0,
            aaguid="",
            fmt=AttestationFormat.NONE,
            credential_type=PublicKeyCredentialType.PUBLIC_KEY,
            user_verified=True,
            attestation_object=b"",
            credential_device_type=CredentialDeviceType.SINGLE_DEVICE,
            credential_backed_up=False,
        )

    monkeypatch.setattr(passkeys_service, "verify_registration_response", _fake_reg)
    client_passkeys_db.post(
        "/auth/passkeys/register/finish",
        json={
            "challenge_token": ct,
            "credential": {"id": "x", "rawId": "eA", "response": {}, "type": "public-key"},
        },
        headers={"Authorization": f"Bearer {tok}"},
    )
    pk = db.query(AuthPasskey).one()
    pk.revoked_at = _utcnow()
    db.commit()

    lst = client_passkeys_db.post("/auth/passkeys/login/start", json={"email": email})
    assert lst.status_code == 200
    from webauthn.helpers import bytes_to_base64url

    raw_b64 = bytes_to_base64url(b"revoked-cred")
    lf = client_passkeys_db.post(
        "/auth/passkeys/login/finish",
        json={
            "challenge_token": lst.json()["challenge_token"],
            "credential": {
                "id": raw_b64,
                "rawId": raw_b64,
                "response": {"clientDataJSON": "e30", "authenticatorData": "Eg", "signature": "sig"},
                "type": "public-key",
            },
        },
        headers={"X-Device-ID": "d1"},
    )
    assert lf.status_code == 401


def test_security_event_on_register_start(client_passkeys_db, db, monkeypatch):
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "true")
    monkeypatch.setenv("WEBAUTHN_RP_ID", "localhost")
    monkeypatch.setenv("WEBAUTHN_ORIGINS", "http://testserver")
    from database import AuthSecurityEvent

    tok = _user_token(client_passkeys_db, db, "pk_evt@example.com", "secret6")
    client_passkeys_db.post(
        "/auth/passkeys/register/start",
        json={},
        headers={"Authorization": f"Bearer {tok}"},
    )
    n = (
        db.query(AuthSecurityEvent)
        .filter(AuthSecurityEvent.event_type == "auth.passkey.register.started")
        .count()
    )
    assert n >= 1


def test_cleanup_removes_expired_challenge(db):
    from services.auth.webauthn_challenges_cleanup import cleanup_webauthn_challenges

    past = _utcnow() - timedelta(hours=1)
    ch = AuthWebAuthnChallenge(
        id=uuid.uuid4(),
        challenge_b64="cleanuptestchallengeb64urlnodup",
        flow_type="login",
        user_id=None,
        identifier="clean@example.com",
        expires_at=past,
    )
    db.add(ch)
    db.flush()
    n = cleanup_webauthn_challenges(db)
    assert n >= 1
    assert db.query(AuthWebAuthnChallenge).filter(AuthWebAuthnChallenge.id == ch.id).first() is None


def test_prompt_accepts_valid_event(client_passkeys_db):
    r = client_passkeys_db.post(
        "/auth/passkeys/prompt",
        json={"event": "auth.passkey.prompt.opened", "identifier_domain": "example.com"},
        headers={"X-Device-ID": "dev-prompt"},
    )
    assert r.status_code == 204


def test_prompt_rejects_invalid_event(client_passkeys_db):
    r = client_passkeys_db.post(
        "/auth/passkeys/prompt",
        json={"event": "not.a.real.event"},
    )
    assert r.status_code == 400
