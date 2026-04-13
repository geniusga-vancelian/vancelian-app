"""Logique OTP SMS partagée : inscription (2FA), connexion mobile admin, tests.

Même génération que [TwoFactorService] (TWO_FACTOR_DEV_FIXED_CODE + code aléatoire 6 chiffres),
même hachage bcrypt pour stockage et vérification.
"""
from __future__ import annotations

import secrets

import bcrypt

from services.security.two_factor_env import two_factor_dev_fixed_code

SMS_OTP_LENGTH = 6
SMS_CODE_TTL_MINUTES = 5
SMS_MAX_VERIFY_ATTEMPTS = 5


def new_plaintext_sms_otp() -> str:
    """Code OTP 6 chiffres pour envoi SMS (aligné sur TwoFactorService._otp_plaintext_for_sms_email)."""
    fixed = two_factor_dev_fixed_code()
    if fixed:
        return fixed
    return f"{secrets.randbelow(900_000) + 100_000:0{SMS_OTP_LENGTH}d}"


def otp_plaintext_for_login_challenges() -> str:
    """OTP texte pour défis login (SMS admin, e-mail admin) — même règle dev [TWO_FACTOR_DEV_FIXED_CODE]."""
    return new_plaintext_sms_otp()


def hash_sms_otp(code: str) -> str:
    return bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_sms_otp(code: str, code_hash: str) -> bool:
    try:
        return bcrypt.checkpw(code.encode("utf-8"), code_hash.encode("ascii"))
    except Exception:  # noqa: BLE001
        return False
