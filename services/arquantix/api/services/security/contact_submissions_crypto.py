"""Chiffrement des soumissions contact (pilote Tier 1) — double écriture + lecture admin."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from database import ContactSubmission

if TYPE_CHECKING:
    from services.security.zero_trust.request_security_context import RequestSecurityContext
from services.security.crypto_access import encrypt_value, safe_decrypt
from services.security.crypto_service import (
    crypto_feature_contact_enabled,
    is_encryption_configured,
    is_v1_ciphertext,
    mask_email,
    mask_freeform,
    strip_plaintext_after_encrypt_contact,
)


def encrypt_and_assign_contact_fields(
    row: ContactSubmission,
    *,
    name: str,
    email: str,
    message: str,
) -> None:
    if not crypto_feature_contact_enabled():
        row.name = name
        row.email = email
        row.message = message
        return
    if not is_encryption_configured():
        raise RuntimeError("APPLICATION_ENCRYPT_CONTACT_SUBMISSIONS requires CRYPTO_LOCAL_MASTER_KEY_B64 or KMS")
    row.name_encrypted = encrypt_value(
        name, purpose="contact_submission_write", operation_id="public_contact_form"
    )
    row.email_encrypted = encrypt_value(
        email, purpose="contact_submission_write", operation_id="public_contact_form"
    )
    row.message_encrypted = encrypt_value(
        message, purpose="contact_submission_write", operation_id="public_contact_form"
    )
    if strip_plaintext_after_encrypt_contact():
        row.name = ""
        row.email = ""
        row.message = ""
    else:
        row.name = name
        row.email = email
        row.message = message


def contact_row_to_public_response_dict(
    row: ContactSubmission,
    *,
    submitted_name: str,
    submitted_email: str,
    submitted_message: str,
) -> Dict[str, Any]:
    """Réponse publique : ne pas renvoyer de clair si strip actif."""
    if crypto_feature_contact_enabled() and strip_plaintext_after_encrypt_contact():
        return {
            "id": row.id,
            "name": mask_freeform(submitted_name),
            "email": mask_email(submitted_email),
            "message": "[encrypted]",
            "ip": row.ip,
            "user_agent": row.user_agent,
            "created_at": row.created_at,
        }
    return {
        "id": row.id,
        "name": row.name,
        "email": row.email,
        "message": row.message,
        "ip": row.ip,
        "user_agent": row.user_agent,
        "created_at": row.created_at,
    }


def contact_row_to_admin_dict(
    row: ContactSubmission,
    *,
    security_context: Optional["RequestSecurityContext"] = None,
) -> Dict[str, Any]:
    decrypt_ok = True
    if security_context is not None:
        from services.security.zero_trust.data_access_control import decryption_allowed

        decrypt_ok, _zt = decryption_allowed(
            security_context,
            purpose="contact_submission_read",
            resource=f"contact:{row.id}",
        )

    def _read(enc_col: str, plain_col: str) -> str:
        if not decrypt_ok:
            return "[zero_trust_masked]"
        enc = getattr(row, enc_col, None)
        plain = getattr(row, plain_col, None)
        if enc and is_v1_ciphertext(enc):

            def _corrupt(_e: Exception) -> str:
                return "[decryption_failed]"

            return safe_decrypt(
                enc,
                purpose="contact_submission_read",
                operation_id="admin_list_contact_submissions",
                on_error=_corrupt,
            ) or ""
        return plain or ""

    return {
        "id": row.id,
        "name": _read("name_encrypted", "name"),
        "email": _read("email_encrypted", "email"),
        "message": _read("message_encrypted", "message"),
        "ip": row.ip,
        "user_agent": row.user_agent,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
