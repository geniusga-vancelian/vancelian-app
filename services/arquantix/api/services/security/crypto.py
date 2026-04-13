"""Fernet helpers for TOTP secret storage in person.profile_json.

Rotation: introduce TWO_FACTOR_TOTP_MASTER_KEY v2 + decrypt-with-old / re-encrypt-with-new
in a controlled migration (not implemented here); production must use a dedicated key
(min 32 chars), validated at boot by two_factor_config_guard.
"""
from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet


def _fernet_from_env() -> Optional[Fernet]:
    raw = os.getenv("TWO_FACTOR_TOTP_MASTER_KEY") or os.getenv("JWT_SECRET_KEY")
    if not raw:
        return None
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_totp_secret(plain_base32: str) -> Optional[str]:
    f = _fernet_from_env()
    if f is None:
        return None
    return f.encrypt(plain_base32.encode("utf-8")).decode("ascii")


def decrypt_totp_secret(token: str) -> Optional[str]:
    f = _fernet_from_env()
    if f is None:
        return None
    try:
        return f.decrypt(token.encode("ascii")).decode("utf-8")
    except Exception:
        return None
