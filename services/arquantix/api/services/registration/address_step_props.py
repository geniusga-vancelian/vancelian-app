"""Stable props schema + validation + normalization for `address_step` components."""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, Optional

ADDRESS_STEP_FIELD_KEYS: FrozenSet[str] = frozenset(
    {
        "postal_code",
        "address_line_1",
        "address_line_2",
        "city",
        "country_of_residence",
    }
)

# Aligned with governance.SUPPORTED_LANGUAGES; extra 2-letter keys allowed for forward compat.
def _is_lang_key(k: str) -> bool:
    return len(k) == 2 and k.isalpha()


def validate_address_step_props_json(pj: Dict[str, Any]) -> None:
    """Raise HTTPException(422) if props violate the address_step schema."""
    from fastapi import HTTPException

    def _flat_i18n(name: str, raw: Any) -> None:
        if raw is None:
            return
        if not isinstance(raw, dict):
            raise HTTPException(
                status_code=422,
                detail=f"address_step {name} must be a JSON object (locale → string)",
            )
        for lk, lv in raw.items():
            if not isinstance(lk, str) or not _is_lang_key(lk.lower()):
                raise HTTPException(
                    status_code=422,
                    detail=f"address_step {name} keys must be 2-letter language codes",
                )
            if not isinstance(lv, str):
                raise HTTPException(
                    status_code=422,
                    detail=f"address_step {name}.{lk} must be a string",
                )

    _flat_i18n("title_i18n", pj.get("title_i18n"))
    _flat_i18n("subtitle_i18n", pj.get("subtitle_i18n"))
    _flat_i18n("search_label_i18n", pj.get("search_label_i18n"))
    _flat_i18n("manual_entry_label_i18n", pj.get("manual_entry_label_i18n"))

    def _field_map(name: str, raw: Any) -> None:
        if raw is None:
            return
        if not isinstance(raw, dict):
            raise HTTPException(
                status_code=422,
                detail=f"address_step {name} must be a JSON object (field_key → string | locale map)",
            )
        for fk, entry in raw.items():
            if fk not in ADDRESS_STEP_FIELD_KEYS:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"address_step {name} unknown field key '{fk}' "
                        f"(allowed: {', '.join(sorted(ADDRESS_STEP_FIELD_KEYS))})"
                    ),
                )
            if isinstance(entry, str):
                continue
            if isinstance(entry, dict):
                for lk, lv in entry.items():
                    if not isinstance(lk, str) or not _is_lang_key(lk.lower()):
                        raise HTTPException(
                            status_code=422,
                            detail=f"address_step {name}.{fk} locale keys must be 2-letter codes",
                        )
                    if not isinstance(lv, str):
                        raise HTTPException(
                            status_code=422,
                            detail=f"address_step {name}.{fk} values must be strings",
                        )
                continue
            raise HTTPException(
                status_code=422,
                detail=f"address_step {name}.{fk} must be a string or a locale object",
            )

    _field_map("field_labels_i18n", pj.get("field_labels_i18n"))
    _field_map("field_placeholders_i18n", pj.get("field_placeholders_i18n"))

    for legacy in ("title", "subtitle", "search_label", "manual_entry_label"):
        v = pj.get(legacy)
        if v is not None and not isinstance(v, str):
            raise HTTPException(
                status_code=422,
                detail=f"address_step {legacy} must be a string when provided (legacy alias)",
            )


def normalize_address_step_props(props: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Copy props and merge legacy string keys into *_i18n maps for clients.

    - Preserves original keys (title, search_label, …) for older clients.
    - Fills missing locale entries from legacy strings where *_i18n is partial.
    """
    if not isinstance(props, dict):
        return {}
    out: Dict[str, Any] = dict(props)

    def _merge_i18n(i18n_key: str, legacy_key: str) -> None:
        merged: Dict[str, str] = {}
        raw = out.get(i18n_key)
        if isinstance(raw, dict):
            for lk, lv in raw.items():
                if (
                    isinstance(lk, str)
                    and _is_lang_key(lk.lower())
                    and isinstance(lv, str)
                    and lv.strip()
                ):
                    merged[lk.lower()] = lv.strip()
        leg = out.get(legacy_key)
        if isinstance(leg, str) and leg.strip():
            for lang in ("en", "fr"):
                if lang not in merged:
                    merged[lang] = leg.strip()
        if merged:
            out[i18n_key] = merged

    _merge_i18n("title_i18n", "title")
    _merge_i18n("subtitle_i18n", "subtitle")
    _merge_i18n("search_label_i18n", "search_label")
    _merge_i18n("manual_entry_label_i18n", "manual_entry_label")

    # Normalize field maps: allow string values → expand to en+fr for convenience
    for map_key in ("field_labels_i18n", "field_placeholders_i18n"):
        raw = out.get(map_key)
        if not isinstance(raw, dict):
            continue
        norm: Dict[str, Any] = {}
        for fk, entry in raw.items():
            if fk not in ADDRESS_STEP_FIELD_KEYS:
                continue
            if isinstance(entry, str) and entry.strip():
                s = entry.strip()
                norm[fk] = {"en": s, "fr": s}
            elif isinstance(entry, dict):
                inner: Dict[str, str] = {}
                for lk, lv in entry.items():
                    if (
                        isinstance(lk, str)
                        and _is_lang_key(lk.lower())
                        and isinstance(lv, str)
                        and lv.strip()
                    ):
                        inner[lk.lower()] = lv.strip()
                if inner:
                    norm[fk] = inner
        if norm:
            out[map_key] = norm

    return out
