"""Helpers for `address_autocomplete` and `address_step` registration components."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

ADDRESS_METADATA_MAX_BYTES = int(os.getenv("ADDRESS_METADATA_MAX_BYTES", "8192"))

# Client → server: optional traceability (stripped before persisting these keys as slugs)
REG_ADDRESS_SOURCES_KEY = "__reg_address_sources__"
REG_ADDRESS_OVERRIDE_KEY = "__reg_address_override__"

VALID_ADDRESS_SOURCES = frozenset({"google_places", "manual", "hybrid"})

DEFAULT_BINDING_SLUGS = {
    "street": "address_line_1",
    "postal": "postal_code",
    "city": "city",
    "country": "country_of_residence",
}

DEFAULT_ADDRESS_STEP_BINDING_SLUGS = {
    "postal_code": "postal_code",
    "address_line_1": "address_line_1",
    "address_line_2": "address_line_2",
    "city": "city",
    "country_of_residence": "country_of_residence",
}


def resolved_binding_slugs(props: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Return street/postal/city/country slug mapping (defaults if props missing)."""
    p = props if isinstance(props, dict) else {}
    raw = p.get("binding_slugs")
    out = dict(DEFAULT_BINDING_SLUGS)
    if isinstance(raw, dict):
        for k in ("street", "postal", "city", "country"):
            v = raw.get(k)
            if isinstance(v, str) and v.strip():
                out[k] = v.strip()
    return out


def metadata_slug_from_props(props: Optional[Dict[str, Any]]) -> Optional[str]:
    p = props if isinstance(props, dict) else {}
    s = p.get("metadata_slug")
    if isinstance(s, str) and s.strip():
        return s.strip()
    if p.get("store_place_id") is True:
        return "address_metadata"
    return None


def all_bound_slugs(props: Optional[Dict[str, Any]]) -> List[str]:
    m = resolved_binding_slugs(props)
    slugs = list(m.values())
    ms = metadata_slug_from_props(props)
    if ms:
        slugs.append(ms)
    return slugs


def resolved_address_step_binding_slugs(props: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Return postal/line1/line2/city/country slug mapping (defaults if props missing)."""
    p = props if isinstance(props, dict) else {}
    raw = p.get("binding_slugs")
    out = dict(DEFAULT_ADDRESS_STEP_BINDING_SLUGS)
    if isinstance(raw, dict):
        for k in DEFAULT_ADDRESS_STEP_BINDING_SLUGS:
            v = raw.get(k)
            if isinstance(v, str) and v.strip():
                out[k] = v.strip()
    return out


def all_bound_slugs_address_step(props: Optional[Dict[str, Any]]) -> List[str]:
    m = resolved_address_step_binding_slugs(props)
    slugs = list(m.values())
    ms = metadata_slug_from_props(props)
    if ms:
        slugs.append(ms)
    return slugs


def normalize_sources_map(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            continue
        if not isinstance(v, str):
            continue
        vs = v.strip()
        if vs in VALID_ADDRESS_SOURCES:
            out[k] = vs
    return out


def allowed_countries_iso2_from_props(props: Optional[Dict[str, Any]]) -> List[str]:
    """ISO2 list from props_json.allowed_countries (strings or {iso2}). Max 25."""
    p = props if isinstance(props, dict) else {}
    raw = p.get("allowed_countries")
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    seen = set()
    for e in raw:
        iso: Optional[str] = None
        if isinstance(e, str) and len(e.strip()) == 2 and e.strip().isalpha():
            iso = e.strip().upper()
        elif isinstance(e, dict):
            v = e.get("iso2") or e.get("value")
            if isinstance(v, str) and len(v.strip()) == 2 and v.strip().isalpha():
                iso = v.strip().upper()
        if iso and iso not in seen:
            seen.add(iso)
            out.append(iso)
        if len(out) >= 25:
            break
    return out


def clamp_address_metadata_value(value: Any) -> Any:
    """Bound JSON size for persisted address_metadata; strip client-supplied raw."""
    if value is None:
        return None
    if not isinstance(value, dict):
        return value
    data = {k: v for k, v in value.items() if k != "raw"}
    try:
        encoded = json.dumps(data, default=str, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        return {"source": "manual", "truncated": True}
    if len(encoded) <= ADDRESS_METADATA_MAX_BYTES:
        return data
    slim = {
        k: data[k]
        for k in ("source", "place_id", "confidence_score")
        if k in data
    }
    try:
        enc2 = json.dumps(slim, default=str, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        return {"source": "manual", "truncated": True}
    if len(enc2) <= ADDRESS_METADATA_MAX_BYTES:
        slim["truncated"] = True
        return slim
    return {"source": str(data.get("source", "manual"))[:32], "truncated": True}
