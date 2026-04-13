"""Public proxy routes for address autocomplete (Google Places) — API key server-only."""
from __future__ import annotations

import os
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status

from .google_places_service import (
    GooglePlacesConfigError,
    autocomplete,
    get_place_details,
)
from .observability import log_autocomplete_details, log_autocomplete_request
from .rate_limiter import get_address_rate_limiter


router = APIRouter(prefix="/api/address", tags=["Address"])

_ALLOWED_COUNTRIES_RE = re.compile(r"^[A-Z]{2}(,[A-Z]{2})*$")
_COUNTRY_ISO2_PARAM_RE = re.compile(r"^[A-Za-z]{2}$")


def _parse_country_query_param(raw: Optional[str]) -> Optional[str]:
    """Single ISO 3166-1 alpha-2 for strict residence-scoped autocomplete."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    u = s.upper()
    if not _COUNTRY_ISO2_PARAM_RE.match(s) or not u.isalpha():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "invalid_country",
                "message": "country must be exactly 2 letters (ISO 3166-1 alpha-2).",
            },
        )
    return u


def _parse_allowed_countries_param(raw: Optional[str]) -> Optional[List[str]]:
    if not raw or not raw.strip():
        return None
    s = raw.strip().upper().replace(" ", "")
    if not _ALLOWED_COUNTRIES_RE.match(s):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "invalid_allowed_countries",
                "message": "allowed_countries must be comma-separated ISO 3166-1 alpha-2 codes (max 25).",
            },
        )
    parts = [p for p in s.split(",") if p]
    # Déduplication, ordre conservé. Ne pas tronquer ici : la limite Google (5 pays) est appliquée
    # dans google_places_service lors de l’appel Places ; tronquer à la parse cassait la validation
    # quand `country` était au-delà des N premiers codes (ex. liste triée longue).
    seen = set()
    out: List[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out if out else None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


def _include_raw_details() -> bool:
    return (os.getenv("ADDRESS_DETAILS_INCLUDE_RAW") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


@router.get("/autocomplete")
def address_autocomplete(
    request: Request,
    q: str = Query("", min_length=0, max_length=256),
    session_id: Optional[str] = Query(None, max_length=64),
    region: Optional[str] = Query(None, min_length=2, max_length=2),
    allowed_countries: Optional[str] = Query(None, max_length=80),
    country: Optional[str] = Query(
        None,
        min_length=2,
        max_length=2,
        description="Residence ISO2 — when set, autocomplete is restricted to this country only.",
    ),
):
    """Proxy Places Autocomplete. `session_id` reserved for future session-bound limits."""
    _ = session_id
    client_key = _client_ip(request)
    limiter = get_address_rate_limiter()
    limiter.check_autocomplete(client_key)

    countries = _parse_allowed_countries_param(allowed_countries)
    country_iso = _parse_country_query_param(country)
    if country_iso is not None:
        # `country` (résidence) = source de vérité pour le périmètre autocomplete Places.
        countries = [country_iso]

    try:
        predictions, err = autocomplete(q, region=region, countries=countries)
    except GooglePlacesConfigError as exc:
        log_autocomplete_request(
            client_key=client_key,
            q_len=len(q.strip()),
            predictions_count=0,
            status="config_error",
            allowed_countries_n=len(countries or []),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if err and not predictions:
        log_autocomplete_request(
            client_key=client_key,
            q_len=len(q.strip()),
            predictions_count=0,
            status="upstream_error",
            allowed_countries_n=len(countries or []),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Places autocomplete failed: {err}",
        )

    pred_n = len(predictions)
    log_autocomplete_request(
        client_key=client_key,
        q_len=len(q.strip()),
        predictions_count=pred_n,
        status="zero_results" if pred_n == 0 and not err else "ok",
        allowed_countries_n=len(countries or []),
    )
    return {"predictions": predictions}


@router.get("/details")
def address_details(
    request: Request,
    place_id: str = Query(..., min_length=1, max_length=256),
    allowed_countries: Optional[str] = Query(None, max_length=80),
    country: Optional[str] = Query(
        None,
        min_length=2,
        max_length=2,
        description="Expected residence ISO2 — narrows validation like autocomplete.",
    ),
):
    """Place details; optional ``country`` / ``allowed_countries`` enforce ISO2 vs parsed result."""
    client_key = _client_ip(request)
    limiter = get_address_rate_limiter()
    limiter.check_details(client_key)

    countries = _parse_allowed_countries_param(allowed_countries)
    country_iso = _parse_country_query_param(country)
    if country_iso is not None:
        # Aligné sur /autocomplete : le pays de résidence impose la validation côté détails.
        countries = [country_iso]

    try:
        detail, err = get_place_details(
            place_id,
            allowed_countries=countries,
            include_raw=_include_raw_details(),
        )
    except GooglePlacesConfigError as exc:
        log_autocomplete_details(client_key=client_key, status="config_error")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if err == "country_not_allowed":
        log_autocomplete_details(
            client_key=client_key,
            status="country_rejected",
            country_ok=False,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "address_country_mismatch",
                "message": "This place is outside the allowed countries for this step.",
                "field": "country_of_residence",
            },
        )

    if err or not detail:
        log_autocomplete_details(client_key=client_key, status="upstream_error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Place details failed: {err or 'empty'}",
        )

    log_autocomplete_details(
        client_key=client_key,
        status="ok",
        partial_match=detail.get("partial_match"),
        country_ok=True,
    )
    return detail
