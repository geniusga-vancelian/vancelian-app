"""Normalisation chemin + corps pour signatures device sensibles (PR D4.1)."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

from fastapi import HTTPException, status

logger = logging.getLogger("arquantix.auth.device_sig_norm")


def normalize_signature_path(path: str) -> str:
    """
    Chemin stable pour ARQXD3 et pour les nonces scopées par route.

    - ``request.url.path`` (sans query) — pas de changement côté query string.
    - Slash final supprimé sauf pour la racine ``/``.
    - Séquences ``//`` réduites (ex. ``/a//b`` → ``/a/b``).
    """
    if not path:
        return "/"
    p = path.strip()
    while "//" in p:
        p = p.replace("//", "/")
    if p != "/" and p.endswith("/"):
        p = p.rstrip("/")
    return p or "/"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_body_sha256_for_sensitive_signature(
    *,
    raw_body: bytes,
    content_type: Optional[str],
    header_sha256_hex: str,
) -> str:
    """
    Détermine le hash SHA-256 du corps utilisé pour vérifier ARQXD3.

    - **Rétrocompat** : ``X-Content-SHA256`` == SHA256(octets bruts du corps).
    - **JSON canonique** : même en-tête peut transporter SHA256(JSON trié, séparateurs compacts) ;
      le client signe la valeur qu’il place dans l’en-tête (l’une ou l’autre convention).
    """
    want = (header_sha256_hex or "").strip().lower()
    if len(want) != 64 or any(c not in "0123456789abcdef" for c in want):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Content-SHA256 must be sha256 hex (64 chars)",
        )

    raw_digest = _sha256_hex(raw_body)
    if want == raw_digest:
        return want

    ct = (content_type or "").split(";")[0].strip().lower()
    is_json = ct in (
        "application/json",
        "application/merge-patch+json",
        "application/vnd.api+json",
    )
    if not is_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "device_signature_body_hash_mismatch",
                "message": "X-Content-SHA256 does not match raw request body.",
            },
        )

    canon_digest: Optional[str] = None
    try:
        if raw_body.strip():
            obj = json.loads(raw_body.decode("utf-8"))
            canon = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            canon_digest = _sha256_hex(canon.encode("utf-8"))
        else:
            canon_digest = _sha256_hex(b"")
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        logger.debug("canonical_json_body_skip: %s", e)
        canon_digest = None

    if canon_digest and want == canon_digest:
        return want

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "device_signature_body_hash_mismatch",
            "message": "X-Content-SHA256 must match raw body or canonical JSON (sorted keys, compact).",
        },
    )
