"""Structured logging for address lookup (no PII: no full query, no place_id)."""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("arquantix.address_lookup")


def _client_bucket(client_key: str) -> str:
    """Short stable hash for logs (not reversible to IP)."""
    h = hashlib.sha256(client_key.encode("utf-8", errors="replace")).hexdigest()[:12]
    return h


def log_autocomplete_request(
    *,
    client_key: str,
    q_len: int,
    predictions_count: int,
    status: str,
    allowed_countries_n: int = 0,
) -> None:
    logger.info(
        "address_autocomplete",
        extra={
            "address_event": "autocomplete",
            "client_bucket": _client_bucket(client_key),
            "q_len": q_len,
            "predictions_count": predictions_count,
            "status": status,
            "allowed_countries_n": allowed_countries_n,
        },
    )


def log_autocomplete_details(
    *,
    client_key: str,
    status: str,
    partial_match: Optional[bool] = None,
    country_ok: Optional[bool] = None,
) -> None:
    logger.info(
        "address_details",
        extra={
            "address_event": "details",
            "client_bucket": _client_bucket(client_key),
            "status": status,
            "partial_match": partial_match,
            "country_allowed_ok": country_ok,
        },
    )


def registration_address_submit_payload(trace_map: Dict[str, str], had_override: bool) -> Dict[str, Any]:
    """Summarize sources for registration FIELDS_SUBMITTED (no raw values)."""
    summary: Dict[str, int] = {"google_places": 0, "manual": 0, "hybrid": 0, "user_input": 0}
    for v in trace_map.values():
        if v in ("google_places", "manual", "hybrid"):
            summary[v] += 1
        else:
            summary["user_input"] += 1
    return {
        "address_sources_summary": summary,
        "address_hybrid_or_override": had_override or summary["hybrid"] > 0,
    }
