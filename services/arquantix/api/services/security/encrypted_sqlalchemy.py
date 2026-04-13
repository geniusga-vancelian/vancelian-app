"""
Champ SQLAlchemy chiffré (AES-256-GCM via ``crypto_service``).

- Écriture : chiffrement automatique dans ``process_bind_param``.
- Lecture : déchiffrement dans ``process_result_value`` **uniquement** si
  ``crypto_access.decryption_context(operation_id)`` est actif ; sinon la valeur
  reste le blob ``v1:...`` (évite exposition accidentelle en clair).

Usage typique admin :

    with decryption_context("admin_list_contact_submissions"):
        rows = session.query(Model).all()
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from services.security.crypto_access import (
    _decrypt_op_ctx,
    _strict_decrypt_check,
    decrypt_value,
    decryption_context,
)
from services.security.crypto_service import decrypt as decrypt_raw, encrypt, is_v1_ciphertext

logger = logging.getLogger("arquantix.crypto.orm")


class EncryptedField(TypeDecorator):
    """Colonne texte stockant un ciphertext ``v1:``."""

    impl = Text
    cache_ok = True

    def __init__(self, purpose: str, *args: Any, **kw: Any):
        super().__init__(*args, **kw)
        self.purpose = purpose

    def process_bind_param(self, value: Optional[str], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        if value == "":
            return ""
        return encrypt(value)

    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[str]:
        if value is None or value == "":
            return value
        if not is_v1_ciphertext(value):
            return value
        if not _strict_decrypt_check():
            return decrypt_raw(value)
        op = _decrypt_op_ctx.get()
        if not op:
            logger.warning(
                "EncryptedField.read_without_decrypt_context purpose=%s",
                self.purpose,
            )
            return None
        return decrypt_value(value, purpose=self.purpose, operation_id=op)


# Ré-export pour ``from services.security.encrypted_sqlalchemy import decryption_context``
__all__ = ["EncryptedField", "decryption_context"]
