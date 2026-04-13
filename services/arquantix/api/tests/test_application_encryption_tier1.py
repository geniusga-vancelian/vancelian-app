"""Chiffrement applicatif Tier 1 — AES-GCM, rotation, corruption, pilote contact."""
from __future__ import annotations

import base64
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect as sa_inspect

from database import ContactSubmission, engine, get_db
from main import app
from services.security.crypto_service import (
    CryptoDecryptionError,
    decrypt,
    encrypt,
    invalidate_key_cache,
    is_v1_ciphertext,
)


@pytest.fixture
def client_main_app_db(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def _require_migration_113():
    cols = {c["name"] for c in sa_inspect(engine).get_columns("contact_submissions", schema="public")}
    if "name_encrypted" not in cols:
        pytest.skip("Migration 113 (contact_submissions encrypted columns) requise")


def _fresh_key_b64() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setenv("CRYPTO_KMS_ENABLED", "false")
    monkeypatch.setenv("CRYPTO_LOCAL_MASTER_KEY_B64", _fresh_key_b64())
    invalidate_key_cache()
    ct = encrypt("donnée secrète €")
    assert ct and ct.startswith("v1:")
    assert decrypt(ct) == "donnée secrète €"


def test_decrypt_with_legacy_key_after_rotation(monkeypatch):
    key_a = _fresh_key_b64()
    monkeypatch.setenv("CRYPTO_KMS_ENABLED", "false")
    monkeypatch.setenv("CRYPTO_LOCAL_MASTER_KEY_B64", key_a)
    monkeypatch.delenv("CRYPTO_LEGACY_MASTER_KEY_B64", raising=False)
    invalidate_key_cache()
    blob = encrypt("rotate-me")

    key_b = _fresh_key_b64()
    monkeypatch.setenv("CRYPTO_LOCAL_MASTER_KEY_B64", key_b)
    monkeypatch.setenv("CRYPTO_LEGACY_MASTER_KEY_B64", key_a)
    invalidate_key_cache()
    assert decrypt(blob) == "rotate-me"


def test_corruption_raises(monkeypatch):
    monkeypatch.setenv("CRYPTO_KMS_ENABLED", "false")
    monkeypatch.setenv("CRYPTO_LOCAL_MASTER_KEY_B64", _fresh_key_b64())
    invalidate_key_cache()
    with pytest.raises(CryptoDecryptionError):
        decrypt("v1:" + base64.b64encode(b"short").decode("ascii"))


def test_public_contact_encrypts_when_flagged(client_main_app_db, db, monkeypatch):
    _require_migration_113()
    monkeypatch.setenv("CRYPTO_KMS_ENABLED", "false")
    monkeypatch.setenv("CRYPTO_LOCAL_MASTER_KEY_B64", _fresh_key_b64())
    monkeypatch.setenv("APPLICATION_ENCRYPT_CONTACT_SUBMISSIONS", "true")
    invalidate_key_cache()

    r = client_main_app_db.post(
        "/public/contact",
        json={"name": "Alice", "email": "alice@example.com", "message": "Bonjour"},
    )
    assert r.status_code == 201
    row = db.query(ContactSubmission).order_by(ContactSubmission.id.desc()).first()
    assert row is not None
    assert row.name_encrypted and is_v1_ciphertext(row.name_encrypted)
    assert row.email_encrypted and is_v1_ciphertext(row.email_encrypted)
    assert row.message_encrypted and is_v1_ciphertext(row.message_encrypted)
    assert row.name == "Alice"
