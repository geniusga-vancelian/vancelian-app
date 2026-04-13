"""
Contrôle d’accès au déchiffrement + audit (sans données en clair dans les logs).
"""
from __future__ import annotations

import contextvars
import logging
from contextlib import contextmanager
from typing import Callable, Iterator, Optional, TypeVar, Union

from services.security.crypto_service import CryptoDecryptionError, decrypt as _decrypt_raw, encrypt as _encrypt_raw

logger = logging.getLogger("arquantix.crypto.access")

T = TypeVar("T")

# operation_id autorisés par « purpose » logique
_PURPOSE_OPS: dict[str, frozenset[str]] = {
    "contact_submission_read": frozenset(
        {
            "admin_list_contact_submissions",
            "admin_export_contact_submissions",
            "migration_backfill_contact",
        }
    ),
    "contact_submission_write": frozenset({"public_contact_form", "migration_backfill_contact"}),
}

_decrypt_op_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("crypto_decrypt_op", default=None)


@contextmanager
def decryption_context(operation_id: str) -> Iterator[None]:
    """Contexte requis pour ``decrypt_value`` quand le mode strict est actif."""
    tok = _decrypt_op_ctx.set(operation_id)
    try:
        yield
    finally:
        _decrypt_op_ctx.reset(tok)


def _strict_decrypt_check() -> bool:
    import os

    return (os.getenv("APPLICATION_CRYPTO_STRICT_DECRYPT") or "true").strip().lower() in ("1", "true", "yes")


def assert_decrypt_allowed(*, purpose: str, operation_id: str) -> None:
    allowed = _PURPOSE_OPS.get(purpose)
    if allowed is None:
        raise PermissionError(f"unknown crypto purpose: {purpose}")
    if operation_id not in allowed:
        raise PermissionError(f"operation {operation_id!r} not allowed for purpose {purpose!r}")


def decrypt_value(blob: Optional[str], *, purpose: str, operation_id: Optional[str] = None) -> Optional[str]:
    """
    Déchiffre avec contrôle d’accès.
    Si strict : ``operation_id`` doit être fourni ou présent dans le contexte ``decryption_context``.
    """
    if blob is None:
        return None
    if blob == "":
        return ""
    op = operation_id or _decrypt_op_ctx.get()
    if _strict_decrypt_check():
        if not op:
            raise PermissionError("decrypt_value requires operation_id or decryption_context")
        assert_decrypt_allowed(purpose=purpose, operation_id=op)
    logger.info(
        "crypto.decrypt_ok purpose=%s op=%s ciphertext_len=%s",
        purpose,
        op or "non_strict",
        len(blob),
    )
    return _decrypt_raw(blob)


def encrypt_value(plaintext: Optional[str], *, purpose: str, operation_id: Optional[str] = None) -> Optional[str]:
    """Chiffre ; en mode strict vérifie que l’écriture est autorisée pour ce purpose."""
    if plaintext is None:
        return None
    op = operation_id or _decrypt_op_ctx.get()
    if _strict_decrypt_check() and purpose == "contact_submission_write":
        if not op:
            raise PermissionError("encrypt_value requires operation_id for contact_submission_write")
        assert_decrypt_allowed(purpose=purpose, operation_id=op)
    return _encrypt_raw(plaintext)


def register_decrypt_purpose(purpose: str, allowed_ops: frozenset[str]) -> None:
    """Extension (tests / plugins)."""
    _PURPOSE_OPS[purpose] = allowed_ops


def safe_decrypt(
    blob: Optional[str],
    *,
    purpose: str,
    operation_id: str,
    on_error: Callable[[Exception], T],
) -> Union[Optional[str], T]:
    """Déchiffre sans propager CryptoDecryptionError (ex. admin UI)."""
    try:
        return decrypt_value(blob, purpose=purpose, operation_id=operation_id)
    except CryptoDecryptionError as exc:
        logger.warning("crypto.decrypt_failed purpose=%s op=%s err=%s", purpose, operation_id, type(exc).__name__)
        return on_error(exc)
    except PermissionError:
        raise
