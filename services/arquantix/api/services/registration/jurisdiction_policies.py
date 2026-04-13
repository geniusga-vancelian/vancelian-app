"""Jurisdiction-based allowlists: phone calling country, residence, nationality (DB-driven)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from database import CountryDirectory, JurisdictionCountryPolicy, JurisdictionPolicySettings


def _settings_row(db: Session, jurisdiction_code: str) -> Optional[JurisdictionPolicySettings]:
    if not jurisdiction_code or not jurisdiction_code.strip():
        return None
    jc = jurisdiction_code.strip().upper()
    return (
        db.query(JurisdictionPolicySettings)
        .filter(JurisdictionPolicySettings.jurisdiction_code == jc)
        .first()
    )


def _policy_rows_with_countries(
    db: Session, jurisdiction_code: str
) -> List[Tuple[JurisdictionCountryPolicy, CountryDirectory]]:
    if not jurisdiction_code or not jurisdiction_code.strip():
        return []
    jc = jurisdiction_code.strip().upper()
    return (
        db.query(JurisdictionCountryPolicy, CountryDirectory)
        .join(CountryDirectory, CountryDirectory.iso2 == JurisdictionCountryPolicy.country_iso2)
        .filter(JurisdictionCountryPolicy.jurisdiction_code == jc)
        .filter(CountryDirectory.is_active.is_(True))
        .order_by(JurisdictionCountryPolicy.position, JurisdictionCountryPolicy.country_iso2)
        .all()
    )


def jurisdiction_has_phone_policies(db: Session, jurisdiction_code: str) -> bool:
    if not jurisdiction_code:
        return False
    jc = jurisdiction_code.strip().upper()
    st = _settings_row(db, jc)
    if st and st.inherit_phone_countries_from_residence:
        return jurisdiction_has_residence_policies(db, jc)
    return (
        db.query(JurisdictionCountryPolicy.id)
        .filter(JurisdictionCountryPolicy.jurisdiction_code == jc)
        .filter(JurisdictionCountryPolicy.allow_phone_country_code.is_(True))
        .first()
        is not None
    )


def jurisdiction_has_residence_policies(db: Session, jurisdiction_code: str) -> bool:
    if not jurisdiction_code:
        return False
    jc = jurisdiction_code.strip().upper()
    return (
        db.query(JurisdictionCountryPolicy.id)
        .filter(JurisdictionCountryPolicy.jurisdiction_code == jc)
        .filter(JurisdictionCountryPolicy.allow_residence.is_(True))
        .first()
        is not None
    )


def jurisdiction_has_nationality_policies(db: Session, jurisdiction_code: str) -> bool:
    """True when at least one row allows nationality (enables nationality submit + filtered lists)."""
    if not jurisdiction_code:
        return False
    jc = jurisdiction_code.strip().upper()
    return (
        db.query(JurisdictionCountryPolicy.id)
        .filter(JurisdictionCountryPolicy.jurisdiction_code == jc)
        .filter(JurisdictionCountryPolicy.allow_nationality.is_(True))
        .first()
        is not None
    )


def list_allowed_residence_countries(
    db: Session,
    jurisdiction_code: str,
    lang: str = "en",
    default_lang: str = "en",
) -> List[Dict[str, Any]]:
    """Countries allowed as country_of_residence for this jurisdiction."""
    del lang, default_lang
    rows = _policy_rows_with_countries(db, jurisdiction_code)
    out: List[Dict[str, Any]] = []
    for pol, cd in rows:
        if not pol.allow_residence:
            continue
        out.append(
            {
                "iso2": cd.iso2,
                "dial_code": cd.phone_country_code,
                "label_en": cd.display_name_en,
                "label_fr": cd.display_name_fr,
                "is_default_residence": pol.is_default_residence,
                "is_default_phone": pol.is_default_phone,
            }
        )
    return out


def list_allowed_phone_countries(
    db: Session,
    jurisdiction_code: str,
    lang: str = "en",
    default_lang: str = "en",
) -> List[Dict[str, Any]]:
    """Countries whose calling code is allowed for phone_input for this jurisdiction."""
    del lang, default_lang
    jc = jurisdiction_code.strip().upper() if jurisdiction_code else ""
    rows = _policy_rows_with_countries(db, jurisdiction_code)
    st = _settings_row(db, jc)
    inherit = bool(st.inherit_phone_countries_from_residence) if st else False
    out: List[Dict[str, Any]] = []
    for pol, cd in rows:
        if inherit:
            if not pol.allow_residence:
                continue
        else:
            if not pol.allow_phone_country_code:
                continue
        out.append(
            {
                "iso2": cd.iso2,
                "dial_code": cd.phone_country_code,
                "label_en": cd.display_name_en,
                "label_fr": cd.display_name_fr,
                "is_default_residence": pol.is_default_residence,
                "is_default_phone": pol.is_default_phone,
            }
        )
    return out


def list_allowed_nationality_countries(
    db: Session,
    jurisdiction_code: str,
    lang: str = "en",
    default_lang: str = "en",
) -> List[Dict[str, Any]]:
    """Countries allowed as nationality (binding_slug nationality) for this jurisdiction."""
    del lang, default_lang
    rows = _policy_rows_with_countries(db, jurisdiction_code)
    out: List[Dict[str, Any]] = []
    for pol, cd in rows:
        if not pol.allow_nationality:
            continue
        out.append(
            {
                "iso2": cd.iso2,
                "dial_code": cd.phone_country_code,
                "label_en": cd.display_name_en,
                "label_fr": cd.display_name_fr,
                "is_default_residence": pol.is_default_residence,
                "is_default_phone": pol.is_default_phone,
            }
        )
    return out


def is_residence_country_allowed(db: Session, jurisdiction_code: str, iso2: str) -> bool:
    if not iso2 or not jurisdiction_code:
        return False
    u = iso2.strip().upper()
    return (
        db.query(JurisdictionCountryPolicy.id)
        .filter(JurisdictionCountryPolicy.jurisdiction_code == jurisdiction_code.strip().upper())
        .filter(JurisdictionCountryPolicy.country_iso2 == u)
        .filter(JurisdictionCountryPolicy.allow_residence.is_(True))
        .first()
        is not None
    )


def is_phone_country_allowed(db: Session, jurisdiction_code: str, iso2: str) -> bool:
    if not iso2 or not jurisdiction_code:
        return False
    u = iso2.strip().upper()
    jc = jurisdiction_code.strip().upper()
    st = _settings_row(db, jc)
    if st and st.inherit_phone_countries_from_residence:
        return is_residence_country_allowed(db, jc, u)
    return (
        db.query(JurisdictionCountryPolicy.id)
        .filter(JurisdictionCountryPolicy.jurisdiction_code == jc)
        .filter(JurisdictionCountryPolicy.country_iso2 == u)
        .filter(JurisdictionCountryPolicy.allow_phone_country_code.is_(True))
        .first()
        is not None
    )


def is_nationality_country_allowed(db: Session, jurisdiction_code: str, iso2: str) -> bool:
    if not iso2 or not jurisdiction_code:
        return False
    u = iso2.strip().upper()
    return (
        db.query(JurisdictionCountryPolicy.id)
        .filter(JurisdictionCountryPolicy.jurisdiction_code == jurisdiction_code.strip().upper())
        .filter(JurisdictionCountryPolicy.country_iso2 == u)
        .filter(JurisdictionCountryPolicy.allow_nationality.is_(True))
        .first()
        is not None
    )


def _pick_default_residence_iso(
    db: Session, jc: str, allowed: List[Dict[str, Any]]
) -> Optional[str]:
    if not allowed:
        return None
    st = _settings_row(db, jc)
    if st and st.default_residence_iso2:
        ds = st.default_residence_iso2.strip().upper()
        if any(x["iso2"] == ds for x in allowed):
            return ds
    for x in allowed:
        if x.get("is_default_residence"):
            return x["iso2"]
    return allowed[0]["iso2"]


def _pick_default_phone_iso(
    db: Session, jc: str, allowed: List[Dict[str, Any]]
) -> Optional[str]:
    if not allowed:
        return None
    st = _settings_row(db, jc)
    if st and st.default_phone_iso2:
        dp = st.default_phone_iso2.strip().upper()
        if any(x["iso2"] == dp for x in allowed):
            return dp
    for x in allowed:
        if x.get("is_default_phone"):
            return x["iso2"]
    return allowed[0]["iso2"]


def _pick_default_nationality_iso(allowed: List[Dict[str, Any]]) -> Optional[str]:
    """No is_default_nationality in this phase: first entry in policy order."""
    if not allowed:
        return None
    return allowed[0]["iso2"]


def enrich_registration_component_props(
    db: Session,
    jurisdiction_code: Optional[str],
    component_type: str,
    props: Dict[str, Any],
    lang: str,
    default_lang: str,
    binding_slug: Optional[str] = None,
) -> Dict[str, Any]:
    """Merge runtime allowlists into component props (phone_input / country_picker).

    country_picker enrichment prefers ``props.policy_scope`` (``nationality`` | ``residence``).
    Legacy: when ``policy_scope`` is absent, ``binding_slug == nationality`` still selects
    nationality policy until all flows expose ``policy_scope`` explicitly.
    """
    del lang, default_lang
    if not jurisdiction_code:
        return props
    jc = jurisdiction_code.strip().upper()
    out = dict(props)
    if component_type == "phone_input":
        phone = list_allowed_phone_countries(db, jc)
        if phone:
            out["allowed_phone_countries"] = phone
            default_iso = _pick_default_phone_iso(db, jc, phone)
            if default_iso:
                out["default_phone_country"] = default_iso
    elif component_type == "country_picker":
        scope = str((props or {}).get("policy_scope") or "").strip().lower()
        slug = (binding_slug or "").strip()
        if scope == "nationality" or (not scope and slug == "nationality"):
            if jurisdiction_has_nationality_policies(db, jc):
                nat = list_allowed_nationality_countries(db, jc)
                if nat:
                    out["allowed_countries"] = nat
                    dnat = _pick_default_nationality_iso(nat)
                    if dnat:
                        out["default_country"] = dnat
        else:
            res = list_allowed_residence_countries(db, jc)
            if res:
                out["allowed_countries"] = res
                dc = _pick_default_residence_iso(db, jc, res)
                if dc:
                    out["default_country"] = dc
    elif component_type in ("address_autocomplete", "address_step"):
        if not out.get("allowed_countries"):
            res = list_allowed_residence_countries(db, jc)
            if res:
                out["allowed_countries"] = res
        if component_type == "address_step":
            from .address_step_props import normalize_address_step_props

            out = normalize_address_step_props(out)
    return out
