"""Client-safe messages and HTTP hints for 2FA error codes."""
from __future__ import annotations

from typing import Dict, Tuple

# Maps internal exception codes -> (http_status, external_code, user_message)
_TWO_FACTOR_HTTP_MAP: Dict[str, Tuple[int, str, str]] = {
    "challenge_not_found": (404, "challenge_not_found", "We could not process this request."),
    "not_found": (404, "challenge_not_found", "We could not process this request."),
    "challenge_expired": (410, "challenge_expired", "This code has expired. Request a new one."),
    "challenge_superseded": (410, "challenge_superseded", "This code was replaced. Request a new SMS code."),
    "expired": (410, "challenge_expired", "This code has expired. Request a new one."),
    "invalid_code": (422, "invalid_code", "Invalid code. Please try again."),
    "too_many_attempts": (429, "too_many_attempts", "Too many attempts. Request a new code."),
    "invalid_state": (429, "challenge_not_verifiable", "This verification can no longer be used."),
    "resend_rate_limited": (429, "resend_rate_limited", "Please wait before requesting another code."),
    "rate_limited": (429, "resend_rate_limited", "Please wait before requesting another code."),
    "start_quota_exceeded": (429, "start_quota_exceeded", "Too many verification requests. Try again later."),
    "target_rate_limited": (429, "target_rate_limited", "Too many verification requests. Try again later."),
    "ip_rate_limited": (429, "ip_rate_limited", "Too many verification requests. Try again later."),
    "verify_rate_limited": (429, "verify_rate_limited", "Too many verification attempts. Try again later."),
    "provider_unavailable": (503, "provider_unavailable", "Verification could not be sent. Try again later."),
    "channel_not_available": (503, "channel_not_available", "This verification channel is not available."),
    "purpose_not_allowed": (400, "purpose_not_allowed", "This verification type is not available."),
    "invalid_purpose": (400, "invalid_purpose", "This verification type is not available."),
    "invalid_channel": (400, "invalid_channel", "Unsupported channel."),
    "target_required": (400, "target_required", "A valid destination is required."),
    "target_mismatch": (400, "target_mismatch", "This destination cannot be used for this verification."),
    "totp_not_configured": (400, "totp_not_configured", "Authenticator is not set up for this account."),
    "totp_encrypt_unconfigured": (503, "provider_unavailable", "Verification service is temporarily unavailable."),
    "person_not_found": (403, "unauthorized_2fa_request", "Unable to complete this request."),
    "unauthorized_2fa_request": (403, "unauthorized_2fa_request", "Unable to complete this request."),
}


def http_detail_for_code(internal_code: str, fallback_message: str | None = None) -> Tuple[int, str, str]:
    row = _TWO_FACTOR_HTTP_MAP.get(internal_code)
    if row:
        return row
    msg = fallback_message or "Request could not be completed."
    return (400, internal_code, msg)
