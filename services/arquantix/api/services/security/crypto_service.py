"""
Chiffrement applicatif AES-256-GCM (IV 12 octets aléatoires par enregistrement).

Production : clé enveloppée déchiffrée via AWS KMS (une fois, cache mémoire).
Développement : ``CRYPTO_LOCAL_MASTER_KEY_B64`` (32 octets en base64url/base64).

Format stocké : ``v1:<base64(iv12 || ciphertext+tag)>``.
"""
from __future__ import annotations

import base64
import logging
import os
import threading
from typing import List, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger("arquantix.crypto")

_PREFIX_V1 = "v1:"

_key_lock = threading.Lock()
_cached_keys: Optional[List[bytes]] = None


class CryptoError(Exception):
    """Erreur de chiffrement / déchiffrement."""


class CryptoDecryptionError(CryptoError):
    """Données corrompues, clé incorrecte ou format invalide."""


def is_encryption_configured() -> bool:
    if (os.getenv("CRYPTO_KMS_ENABLED") or "").strip().lower() in ("1", "true", "yes"):
        return bool((os.getenv("CRYPTO_WRAPPED_KEY_B64") or "").strip())
    return bool((os.getenv("CRYPTO_LOCAL_MASTER_KEY_B64") or "").strip())


def crypto_feature_contact_enabled() -> bool:
    return (os.getenv("APPLICATION_ENCRYPT_CONTACT_SUBMISSIONS") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def strip_plaintext_after_encrypt_contact() -> bool:
    """Si true, après chiffrement les colonnes claires sont mises à NULL (après rollout)."""
    return (os.getenv("APPLICATION_ENCRYPTION_STRIP_CONTACT_PLAINTEXT") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _b64decode_key(raw: str) -> bytes:
    s = raw.strip()
    pad = "=" * (-len(s) % 4)
    data = base64.urlsafe_b64decode(s + pad)
    if len(data) != 32:
        raise CryptoError("master key must decode to 32 bytes (AES-256)")
    return data


def _kms_decrypt_wrapped_key() -> bytes:
    import boto3

    key_id = (os.getenv("CRYPTO_MASTER_KEY_ID") or "").strip()
    wrapped_b64 = (os.getenv("CRYPTO_WRAPPED_KEY_B64") or "").strip()
    if not key_id or not wrapped_b64:
        raise CryptoError("CRYPTO_MASTER_KEY_ID and CRYPTO_WRAPPED_KEY_B64 required when CRYPTO_KMS_ENABLED")
    region = (os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "eu-west-1").strip()
    client = boto3.client("kms", region_name=region)
    blob = base64.b64decode(wrapped_b64)
    resp = client.decrypt(CiphertextBlob=blob, KeyId=key_id)
    pt = resp.get("Plaintext") or b""
    if len(pt) != 32:
        raise CryptoError("KMS decrypt did not return a 32-byte AES key")
    return pt


def _load_key_chain() -> List[bytes]:
    """Clé courante en premier, puis clés legacy pour rotation."""
    keys: List[bytes] = []
    kms_on = (os.getenv("CRYPTO_KMS_ENABLED") or "").strip().lower() in ("1", "true", "yes")
    if kms_on:
        keys.append(_kms_decrypt_wrapped_key())
    else:
        local = (os.getenv("CRYPTO_LOCAL_MASTER_KEY_B64") or "").strip()
        if not local:
            raise CryptoError(
                "Set CRYPTO_LOCAL_MASTER_KEY_B64 (32-byte key base64) or enable KMS with CRYPTO_WRAPPED_KEY_B64"
            )
        keys.append(_b64decode_key(local))
    legacy = (os.getenv("CRYPTO_LEGACY_MASTER_KEY_B64") or "").strip()
    if legacy:
        keys.append(_b64decode_key(legacy))
    return keys


def get_data_key_chain() -> List[bytes]:
    """Cache thread-safe de la chaîne de clés (courante + legacy)."""
    global _cached_keys
    with _key_lock:
        if _cached_keys is None:
            _cached_keys = _load_key_chain()
            logger.info("crypto.data_key loaded (keys=%s, kms=%s)", len(_cached_keys), bool(os.getenv("CRYPTO_KMS_ENABLED")))
        return _cached_keys


def invalidate_key_cache() -> None:
    """Tests / rotation : force le rechargement des clés."""
    global _cached_keys
    with _key_lock:
        _cached_keys = None


def encrypt(value: Optional[str]) -> Optional[str]:
    """
    Chiffre une chaîne UTF-8. Retourne ``v1:...`` ou None si entrée None.
    Chaîne vide → chaîne vide (pas de blob).
    """
    if value is None:
        return None
    if value == "":
        return ""
    keys = get_data_key_chain()
    aes = AESGCM(keys[0])
    iv = os.urandom(12)
    ct = aes.encrypt(iv, value.encode("utf-8"), b"")
    blob = base64.b64encode(iv + ct).decode("ascii")
    return f"{_PREFIX_V1}{blob}"


def decrypt(value: Optional[str]) -> Optional[str]:
    """
    Déchiffre un blob ``v1:``. Retourne None si entrée None.
    Lève [CryptoDecryptionError] si corruption ou mauvaise clé.
    """
    if value is None:
        return None
    if value == "":
        return ""
    if not isinstance(value, str) or not value.startswith(_PREFIX_V1):
        raise CryptoDecryptionError("ciphertext must be a v1: blob")
    raw_b64 = value[len(_PREFIX_V1) :]
    try:
        raw = base64.b64decode(raw_b64)
    except Exception as exc:  # noqa: BLE001
        raise CryptoDecryptionError("invalid base64") from exc
    if len(raw) < 12 + 16:
        raise CryptoDecryptionError("truncated ciphertext")
    iv, ctext = raw[:12], raw[12:]
    last_err: Optional[Exception] = None
    for key in get_data_key_chain():
        try:
            aes = AESGCM(key)
            pt = aes.decrypt(iv, ctext, b"")
            return pt.decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue
    raise CryptoDecryptionError("decrypt failed with all configured keys") from last_err


def is_v1_ciphertext(value: Optional[str]) -> bool:
    return isinstance(value, str) and value.startswith(_PREFIX_V1) and len(value) > len(_PREFIX_V1) + 20


def mask_email(value: Optional[str]) -> str:
    if not value or "@" not in value:
        return "***"
    local, _, domain = value.partition("@")
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"


def mask_phone(value: Optional[str]) -> str:
    if not value or len(value) < 4:
        return "***"
    return f"***{value[-4:]}"


def mask_freeform(value: Optional[str], head: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= head:
        return "***"
    return value[:head] + "…"

