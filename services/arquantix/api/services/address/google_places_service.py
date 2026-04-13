"""Google Places (legacy REST) — autocomplete + place details + component parsing."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

GOOGLE_PLACES_AUTOCOMPLETE_URL = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
GOOGLE_PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

_API_ROOT = Path(__file__).resolve().parents[2]


class GooglePlacesConfigError(RuntimeError):
    """Raised when GOOGLE_MAPS_API_KEY is missing."""


def _api_key() -> str:
    key = (os.getenv("GOOGLE_MAPS_API_KEY") or "").strip()
    if not key:
        # Startup may have missed .env (uvicorn --reload does not watch .env by default), or the
        # shell exported an empty GOOGLE_MAPS_API_KEY so load_dotenv did not override.
        try:
            from dotenv import dotenv_values
        except ImportError:
            dotenv_values = None  # type: ignore[misc, assignment]
        if dotenv_values is not None:
            base = dotenv_values(_API_ROOT / ".env") or {}
            local = dotenv_values(_API_ROOT / ".env.local") or {}
            merged = {**base, **local}
            raw = merged.get("GOOGLE_MAPS_API_KEY")
            if raw is not None:
                key = str(raw).strip()
            if key:
                os.environ["GOOGLE_MAPS_API_KEY"] = key
    if not key:
        raise GooglePlacesConfigError("GOOGLE_MAPS_API_KEY is not set")
    return key


def parse_address_components(components: List[Dict[str, Any]]) -> Dict[str, str]:
    """Map Google address_components list to Vancelian-style keys."""
    out: Dict[str, str] = {}
    for c in components:
        types = c.get("types") or []
        if "street_number" in types:
            out["street_number"] = str(c.get("long_name") or c.get("short_name") or "").strip()
        if "route" in types:
            out["route"] = str(c.get("long_name") or c.get("short_name") or "").strip()
        if "postal_code" in types:
            out["postal_code"] = str(c.get("long_name") or c.get("short_name") or "").strip()
        if "locality" in types:
            out["locality"] = str(c.get("long_name") or c.get("short_name") or "").strip()
        if "postal_town" in types and "locality" not in out:
            out["locality"] = str(c.get("long_name") or c.get("short_name") or "").strip()
        if "administrative_area_level_1" in types and "locality" not in out:
            out["locality"] = str(c.get("long_name") or c.get("short_name") or "").strip()
        if "country" in types:
            out["country_short"] = str(c.get("short_name") or "").strip().upper()
            out["country_long"] = str(c.get("long_name") or "").strip()

    street_num = out.get("street_number", "")
    route = out.get("route", "")
    line1 = f"{street_num} {route}".strip()
    out["address_line_1"] = line1
    return out


def _confidence_from_result(partial_match: bool) -> float:
    if partial_match:
        return 0.72
    return 0.95


def _components_param(
    *,
    region: Optional[str],
    countries: Optional[List[str]],
) -> Optional[str]:
    """Google Places: up to 5 countries as country:XX|country:YY."""
    if countries:
        uniq: List[str] = []
        for c in countries:
            u = (c or "").strip().upper()
            if len(u) == 2 and u.isalpha() and u not in uniq:
                uniq.append(u)
            if len(uniq) >= 5:
                break
        if uniq:
            return "|".join(f"country:{c}" for c in uniq)
    if region and len(region.strip()) == 2:
        r = region.strip().upper()
        if r.isalpha():
            return f"country:{r}"
    return None


def autocomplete(
    query: str,
    *,
    region: Optional[str] = None,
    countries: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """Call Places Autocomplete. Returns (predictions, error_message)."""
    q = (query or "").strip()
    if len(q) < 2:
        return [], None

    params: Dict[str, str] = {
        "input": q,
        "key": _api_key(),
        "types": "address",
    }
    comp = _components_param(region=region, countries=countries)
    if comp:
        params["components"] = comp

    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(GOOGLE_PLACES_AUTOCOMPLETE_URL, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        logger.warning("google_places_autocomplete_failed: %s", exc)
        return [], str(exc)

    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        msg = data.get("error_message") or status or "UNKNOWN"
        logger.warning("google_places_autocomplete_status=%s", status)
        return [], str(msg)

    preds = []
    for p in data.get("predictions") or []:
        desc = p.get("description")
        pid = p.get("place_id")
        if isinstance(desc, str) and isinstance(pid, str):
            preds.append({"description": desc, "place_id": pid})
    return preds, None


def get_place_details(
    place_id: str,
    *,
    allowed_countries: Optional[List[str]] = None,
    include_raw: bool = False,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Return normalized detail dict for /api/address/details or error string."""
    pid = (place_id or "").strip()
    if not pid:
        return {}, "place_id required"

    fields = "address_component,formatted_address,geometry/location,place_id,types"
    params = {
        "place_id": pid,
        "fields": fields,
        "key": _api_key(),
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            r = client.get(GOOGLE_PLACES_DETAILS_URL, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        logger.warning("google_places_details_failed: %s", exc)
        return {}, str(exc)

    status = data.get("status")
    if status != "OK":
        msg = data.get("error_message") or status or "UNKNOWN"
        return {}, str(msg)

    res = data.get("result") or {}
    components = res.get("address_components") or []
    if not isinstance(components, list):
        components = []

    parsed = parse_address_components(components)
    loc = (res.get("geometry") or {}).get("location") or {}
    lat = loc.get("lat")
    lng = loc.get("lng")

    partial_match = res.get("partial_match") is True
    conf = _confidence_from_result(bool(partial_match))

    country = (parsed.get("country_short") or "").strip().upper()
    if allowed_countries:
        allow = {
            c.strip().upper()
            for c in allowed_countries
            if len((c or "").strip()) == 2
        }
        # With a non-empty allowlist, require a resolved ISO2 that is in the list
        # (avoids autofill when Google omits country or returns an unexpected region).
        if allow and (not country or country not in allow):
            return {}, "country_not_allowed"

    field_warnings: List[str] = []
    if not (parsed.get("postal_code") or "").strip():
        field_warnings.append("missing_postal_code")
    if not (parsed.get("locality") or "").strip():
        field_warnings.append("missing_city")
    if not (parsed.get("address_line_1") or "").strip():
        field_warnings.append("missing_street")

    out: Dict[str, Any] = {
        "address_line_1": parsed.get("address_line_1") or "",
        "postal_code": parsed.get("postal_code") or "",
        "city": parsed.get("locality") or "",
        "country": country,
        "google_place_id": res.get("place_id") or pid,
        "formatted_address": res.get("formatted_address") or "",
        "confidence_score": conf,
        "lat": float(lat) if lat is not None else None,
        "lng": float(lng) if lng is not None else None,
        "partial_match": partial_match,
        "field_warnings": field_warnings,
        "incomplete": bool(field_warnings),
    }
    if include_raw:
        out["raw"] = {
            "address_components": components,
            "types": res.get("types"),
            "partial_match": res.get("partial_match"),
        }
    return out, None
