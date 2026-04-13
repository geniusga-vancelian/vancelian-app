"""Admin CRUD + presets for jurisdiction country policies (DB source of truth)."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from database import (
    CountryDirectory,
    JurisdictionCountryPolicy,
    JurisdictionPolicySettings,
    RegistrationJurisdiction,
)

# Explicit EU/EEA list aligned with seed migration 099 (excluding AE).
EU_EXPLICIT_ISO2: Tuple[str, ...] = (
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
    "IS",
    "LI",
    "NO",
)


def _jc(code: str) -> str:
    return (code or "").strip().upper()


def ensure_jurisdiction(db: Session, code: str) -> RegistrationJurisdiction:
    j = (
        db.query(RegistrationJurisdiction)
        .filter(RegistrationJurisdiction.code == _jc(code))
        .first()
    )
    if not j:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found")
    return j


def get_or_create_settings(db: Session, jurisdiction_code: str) -> JurisdictionPolicySettings:
    jc = _jc(jurisdiction_code)
    row = (
        db.query(JurisdictionPolicySettings)
        .filter(JurisdictionPolicySettings.jurisdiction_code == jc)
        .first()
    )
    if row:
        return row
    row = JurisdictionPolicySettings(
        id=uuid.uuid4(),
        jurisdiction_code=jc,
        inherit_phone_countries_from_residence=False,
    )
    db.add(row)
    db.flush()
    return row


def policy_summary_for_code(db: Session, code: str) -> Dict[str, Any]:
    jc = _jc(code)
    st = (
        db.query(JurisdictionPolicySettings)
        .filter(JurisdictionPolicySettings.jurisdiction_code == jc)
        .first()
    )
    rows = (
        db.query(JurisdictionCountryPolicy)
        .filter(JurisdictionCountryPolicy.jurisdiction_code == jc)
        .all()
    )
    inherit = bool(st.inherit_phone_countries_from_residence) if st else False
    res_count = sum(1 for r in rows if r.allow_residence)
    nat_count = sum(1 for r in rows if r.allow_nationality)
    if inherit:
        phone_count = res_count
    else:
        phone_count = sum(1 for r in rows if r.allow_phone_country_code)
    return {
        "jurisdiction_code": jc,
        "residence_country_count": res_count,
        "phone_country_count": phone_count,
        "nationality_country_count": nat_count,
        "default_residence_iso2": st.default_residence_iso2 if st else None,
        "default_phone_iso2": st.default_phone_iso2 if st else None,
        "inherit_phone_countries_from_residence": inherit,
        "has_policy_rows": len(rows) > 0,
    }


def policy_summaries_for_codes(db: Session, codes: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    seen = set()
    for c in codes:
        jc = _jc(c)
        if not jc or jc in seen:
            continue
        seen.add(jc)
        out[jc] = policy_summary_for_code(db, jc)
    return out


def list_jurisdictions_policy_overview(db: Session) -> List[Dict[str, Any]]:
    jurs = db.query(RegistrationJurisdiction).order_by(RegistrationJurisdiction.code).all()
    out: List[Dict[str, Any]] = []
    for j in jurs:
        summ = policy_summary_for_code(db, j.code)
        out.append(
            {
                "jurisdiction_id": str(j.id),
                "code": j.code,
                "name": j.name,
                "is_active": j.is_active,
                "residence_country_count": summ["residence_country_count"],
                "phone_country_count": summ["phone_country_count"],
                "nationality_country_count": summ["nationality_country_count"],
                "default_residence_iso2": summ["default_residence_iso2"],
                "default_phone_iso2": summ["default_phone_iso2"],
                "inherit_phone_countries_from_residence": summ[
                    "inherit_phone_countries_from_residence"
                ],
                "has_policy_rows": summ["has_policy_rows"],
            }
        )
    return out


def _serialize_country_row(pol: JurisdictionCountryPolicy, cd: CountryDirectory) -> Dict[str, Any]:
    return {
        "country_iso2": pol.country_iso2,
        "country_iso3": cd.iso3,
        "display_name_en": cd.display_name_en,
        "display_name_fr": cd.display_name_fr,
        "phone_country_code": cd.phone_country_code,
        "allow_residence": pol.allow_residence,
        "allow_phone_country_code": pol.allow_phone_country_code,
        "allow_nationality": pol.allow_nationality,
        "is_default_residence": pol.is_default_residence,
        "is_default_phone": pol.is_default_phone,
        "position": pol.position,
    }


def get_jurisdiction_policy_detail(db: Session, code: str) -> Dict[str, Any]:
    j = ensure_jurisdiction(db, code)
    jc = j.code
    st = (
        db.query(JurisdictionPolicySettings)
        .filter(JurisdictionPolicySettings.jurisdiction_code == jc)
        .first()
    )
    summ = policy_summary_for_code(db, jc)
    rows = (
        db.query(JurisdictionCountryPolicy, CountryDirectory)
        .join(CountryDirectory, CountryDirectory.iso2 == JurisdictionCountryPolicy.country_iso2)
        .filter(JurisdictionCountryPolicy.jurisdiction_code == jc)
        .order_by(JurisdictionCountryPolicy.position, JurisdictionCountryPolicy.country_iso2)
        .all()
    )
    settings_out = (
        {
            "jurisdiction_code": jc,
            "inherit_phone_countries_from_residence": st.inherit_phone_countries_from_residence,
            "default_residence_iso2": st.default_residence_iso2,
            "default_phone_iso2": st.default_phone_iso2,
            "updated_at": st.updated_at.isoformat() if st.updated_at else None,
        }
        if st
        else {
            "jurisdiction_code": jc,
            "inherit_phone_countries_from_residence": False,
            "default_residence_iso2": None,
            "default_phone_iso2": None,
            "updated_at": None,
        }
    )
    return {
        "jurisdiction": {"id": str(j.id), "code": j.code, "name": j.name, "is_active": j.is_active},
        "summary": summ,
        "settings": settings_out,
        "countries": [_serialize_country_row(p, c) for p, c in rows],
    }


def list_country_directory(db: Session) -> List[Dict[str, Any]]:
    rows = (
        db.query(CountryDirectory)
        .order_by(CountryDirectory.iso2)
        .all()
    )
    return [
        {
            "iso2": r.iso2,
            "iso3": r.iso3,
            "display_name_en": r.display_name_en,
            "display_name_fr": r.display_name_fr,
            "phone_country_code": r.phone_country_code,
            "is_active": r.is_active,
        }
        for r in rows
    ]


def _validate_iso_in_directory(db: Session, iso2: str) -> CountryDirectory:
    u = _jc(iso2)
    cd = db.query(CountryDirectory).filter(CountryDirectory.iso2 == u).first()
    if not cd:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown country_iso2: {u}",
        )
    if not cd.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Country {u} is not active in directory",
        )
    return cd


def _apply_settings_defaults_to_row_flags(db: Session, jc: str, st: JurisdictionPolicySettings) -> None:
    rows = (
        db.query(JurisdictionCountryPolicy)
        .filter(JurisdictionCountryPolicy.jurisdiction_code == jc)
        .all()
    )
    dr = st.default_residence_iso2
    dp = st.default_phone_iso2
    for r in rows:
        r.is_default_residence = bool(dr and r.country_iso2 == dr)
        r.is_default_phone = bool(dp and r.country_iso2 == dp)


def patch_settings(db: Session, code: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """updates keys: inherit_phone_countries_from_residence, default_residence_iso2, default_phone_iso2 (None clears)."""
    ensure_jurisdiction(db, code)
    jc = _jc(code)
    st = get_or_create_settings(db, jc)
    if "inherit_phone_countries_from_residence" in updates:
        st.inherit_phone_countries_from_residence = bool(
            updates["inherit_phone_countries_from_residence"]
        )
    if "default_residence_iso2" in updates:
        v = updates["default_residence_iso2"]
        if v is None:
            st.default_residence_iso2 = None
        else:
            vs = str(v).strip().upper()
            _validate_iso_in_directory(db, vs)
            pol = (
                db.query(JurisdictionCountryPolicy)
                .filter(
                    JurisdictionCountryPolicy.jurisdiction_code == jc,
                    JurisdictionCountryPolicy.country_iso2 == vs,
                    JurisdictionCountryPolicy.allow_residence.is_(True),
                )
                .first()
            )
            if not pol:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="default_residence_iso2 must be a country with allow_residence in this jurisdiction",
                )
            st.default_residence_iso2 = vs
    if "default_phone_iso2" in updates:
        v = updates["default_phone_iso2"]
        if v is None:
            st.default_phone_iso2 = None
        else:
            vs = str(v).strip().upper()
            _validate_iso_in_directory(db, vs)
            if not _iso_allowed_for_effective_phone(db, jc, st, vs):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="default_phone_iso2 must be allowed for phone under current rules",
                )
            st.default_phone_iso2 = vs

    _apply_settings_defaults_to_row_flags(db, jc, st)
    db.commit()
    return get_jurisdiction_policy_detail(db, jc)


def _iso_allowed_for_effective_phone(
    db: Session, jc: str, st: JurisdictionPolicySettings, iso2: str
) -> bool:
    pol = (
        db.query(JurisdictionCountryPolicy)
        .filter(
            JurisdictionCountryPolicy.jurisdiction_code == jc,
            JurisdictionCountryPolicy.country_iso2 == iso2,
        )
        .first()
    )
    if not pol:
        return False
    if st.inherit_phone_countries_from_residence:
        return bool(pol.allow_residence)
    return bool(pol.allow_phone_country_code)


def validate_country_payload(
    db: Session,
    jc: str,
    st: JurisdictionPolicySettings,
    rows_in: List[Dict[str, Any]],
) -> None:
    if not rows_in:
        return
    seen_iso = set()
    def_res = [r for r in rows_in if r.get("is_default_residence")]
    def_phone = [r for r in rows_in if r.get("is_default_phone")]
    if len(def_res) > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At most one is_default_residence row",
        )
    if len(def_phone) > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At most one is_default_phone row",
        )
    for raw in rows_in:
        iso = _jc(str(raw.get("country_iso2", "")))
        if not iso or iso in seen_iso:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Duplicate or empty country_iso2",
            )
        seen_iso.add(iso)
        _validate_iso_in_directory(db, iso)
        allow_res = bool(raw.get("allow_residence", False))
        allow_phone = bool(raw.get("allow_phone_country_code", False))
        if raw.get("is_default_residence") and not allow_res:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="is_default_residence requires allow_residence",
            )
        if raw.get("is_default_phone"):
            if st.inherit_phone_countries_from_residence:
                if not allow_res:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="When inherit phone from residence, is_default_phone requires allow_residence",
                    )
            else:
                if not allow_phone:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="is_default_phone requires allow_phone_country_code",
                    )


def replace_country_policies(
    db: Session,
    code: str,
    rows_in: List[Dict[str, Any]],
) -> Dict[str, Any]:
    ensure_jurisdiction(db, code)
    jc = _jc(code)
    st = get_or_create_settings(db, jc)

    db.query(JurisdictionCountryPolicy).filter(
        JurisdictionCountryPolicy.jurisdiction_code == jc
    ).delete(synchronize_session=False)
    db.flush()

    if not rows_in:
        st.default_residence_iso2 = None
        st.default_phone_iso2 = None
        db.commit()
        return get_jurisdiction_policy_detail(db, jc)

    validate_country_payload(db, jc, st, rows_in)

    for i, raw in enumerate(rows_in):
        iso = _jc(str(raw["country_iso2"]))
        db.add(
            JurisdictionCountryPolicy(
                id=uuid.uuid4(),
                jurisdiction_code=jc,
                country_iso2=iso,
                allow_residence=bool(raw.get("allow_residence", False)),
                allow_phone_country_code=bool(raw.get("allow_phone_country_code", False)),
                allow_nationality=bool(raw.get("allow_nationality", False)),
                is_default_residence=bool(raw.get("is_default_residence", False)),
                is_default_phone=bool(raw.get("is_default_phone", False)),
                position=int(raw.get("position", i)),
            )
        )
    db.flush()

    dr = next((r for r in rows_in if r.get("is_default_residence")), None)
    dp = next((r for r in rows_in if r.get("is_default_phone")), None)
    st.default_residence_iso2 = _jc(str(dr["country_iso2"])) if dr else None
    st.default_phone_iso2 = _jc(str(dp["country_iso2"])) if dp else None

    db.commit()
    return get_jurisdiction_policy_detail(db, jc)


def apply_preset(db: Session, code: str, preset: str) -> Dict[str, Any]:
    ensure_jurisdiction(db, code)
    jc = _jc(code)
    st = get_or_create_settings(db, jc)
    p = (preset or "").strip().lower()

    if p == "clear":
        db.query(JurisdictionCountryPolicy).filter(
            JurisdictionCountryPolicy.jurisdiction_code == jc
        ).delete(synchronize_session=False)
        st.default_residence_iso2 = None
        st.default_phone_iso2 = None
        db.commit()
        return get_jurisdiction_policy_detail(db, jc)

    if p in ("mirror_phone_to_residence", "set_phone_equal_residence"):
        rows = (
            db.query(JurisdictionCountryPolicy)
            .filter(JurisdictionCountryPolicy.jurisdiction_code == jc)
            .all()
        )
        if not rows:
            db.commit()
            return get_jurisdiction_policy_detail(db, jc)
        for r in rows:
            r.allow_phone_country_code = r.allow_residence
        db.commit()
        return get_jurisdiction_policy_detail(db, jc)

    if p in ("apply_residence_to_phone", "expand_phone_for_residence"):
        rows = (
            db.query(JurisdictionCountryPolicy)
            .filter(JurisdictionCountryPolicy.jurisdiction_code == jc)
            .all()
        )
        for r in rows:
            if r.allow_residence:
                r.allow_phone_country_code = True
        db.commit()
        return get_jurisdiction_policy_detail(db, jc)

    if p == "eu_from_directory":
        ordered: List[str] = []
        for iso in EU_EXPLICIT_ISO2:
            cd = (
                db.query(CountryDirectory)
                .filter(
                    CountryDirectory.iso2 == iso,
                    CountryDirectory.is_active.is_(True),
                )
                .first()
            )
            if cd:
                ordered.append(iso)
        rows_payload = [
            {
                "country_iso2": iso,
                "allow_residence": True,
                "allow_phone_country_code": True,
                "allow_nationality": True,
                "is_default_residence": iso == "FR",
                "is_default_phone": iso == "FR",
                "position": pos,
            }
            for pos, iso in enumerate(ordered)
        ]
        if not rows_payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No EU countries found in country_directory",
            )
        return replace_country_policies(db, jc, rows_payload)

    if p == "eu_explicit":
        rows_payload: List[Dict[str, Any]] = []
        for pos, iso in enumerate(EU_EXPLICIT_ISO2):
            rows_payload.append(
                {
                    "country_iso2": iso,
                    "allow_residence": True,
                    "allow_phone_country_code": True,
                    "allow_nationality": True,
                    "is_default_residence": iso == "FR",
                    "is_default_phone": iso == "FR",
                    "position": pos,
                }
            )
        return replace_country_policies(db, jc, rows_payload)

    if p == "uae_explicit":
        return replace_country_policies(
            db,
            jc,
            [
                {
                    "country_iso2": "AE",
                    "allow_residence": True,
                    "allow_phone_country_code": True,
                    "allow_nationality": True,
                    "is_default_residence": True,
                    "is_default_phone": True,
                    "position": 0,
                }
            ],
        )

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=(
            f"Unknown preset: {preset}. "
            "Use clear, eu_explicit, eu_from_directory, uae_explicit, "
            "mirror_phone_to_residence, apply_residence_to_phone."
        ),
    )
