"""Admin API: jurisdiction country policies + settings + country directory."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db

from . import jurisdiction_policy_admin_service as jps

router = APIRouter(prefix="/api/admin/jurisdiction-policies", tags=["Jurisdiction policies"])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------


class SettingsPatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inherit_phone_countries_from_residence: Optional[bool] = None
    default_residence_iso2: Optional[str] = None
    default_phone_iso2: Optional[str] = None


class CountryPolicyRowIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country_iso2: str = Field(..., min_length=2, max_length=2)
    allow_residence: bool = False
    allow_phone_country_code: bool = False
    allow_nationality: bool = False
    is_default_residence: bool = False
    is_default_phone: bool = False
    position: int = 0


class PatchCountriesBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: List[CountryPolicyRowIn] = Field(default_factory=list)


class ApplyPresetBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: str = Field(..., min_length=1)


# ------------------------------------------------------------------
# Jurisdiction policies
# ------------------------------------------------------------------


@router.get("")
def list_jurisdiction_policies(db: Session = Depends(get_db)):
    return jps.list_jurisdictions_policy_overview(db)


@router.get("/{code}")
def get_jurisdiction_policy(code: str, db: Session = Depends(get_db)):
    return jps.get_jurisdiction_policy_detail(db, code)


@router.patch("/{code}/settings")
def patch_jurisdiction_settings(
    code: str,
    body: SettingsPatchBody,
    db: Session = Depends(get_db),
):
    raw = body.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=400, detail="No fields to update")
    return jps.patch_settings(db, code, raw)


@router.patch("/{code}/countries")
def patch_jurisdiction_countries(
    code: str,
    body: PatchCountriesBody,
    db: Session = Depends(get_db),
):
    rows = [r.model_dump() for r in body.rows]
    return jps.replace_country_policies(db, code, rows)


@router.post("/{code}/apply-preset")
def apply_jurisdiction_preset(
    code: str,
    body: ApplyPresetBody,
    db: Session = Depends(get_db),
):
    return jps.apply_preset(db, code, body.preset)


# ------------------------------------------------------------------
# Backward-compatible path (read-only list of country rows)
# ------------------------------------------------------------------

legacy_router = APIRouter(prefix="/api/admin/jurisdictions", tags=["Jurisdiction policies (legacy)"])


@legacy_router.get("/{code}/country-policies")
def list_country_policies_legacy(code: str, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    jc = (code or "").strip().upper()
    if not jc:
        raise HTTPException(status_code=400, detail="Invalid jurisdiction code")
    detail = jps.get_jurisdiction_policy_detail(db, code)
    out: List[Dict[str, Any]] = []
    for row in detail.get("countries", []):
        out.append(
            {
                "jurisdiction_code": jc,
                "country_iso2": row["country_iso2"],
                "country_iso3": row["country_iso3"],
                "display_name_en": row["display_name_en"],
                "display_name_fr": row["display_name_fr"],
                "phone_country_code": row["phone_country_code"],
                "allow_residence": row["allow_residence"],
                "allow_phone_country_code": row["allow_phone_country_code"],
                "allow_nationality": row["allow_nationality"],
                "is_default_residence": row["is_default_residence"],
                "is_default_phone": row["is_default_phone"],
                "position": row["position"],
            }
        )
    return out


country_directory_admin_router = APIRouter(prefix="/api/admin", tags=["Country directory"])


@country_directory_admin_router.get("/country-directory")
def get_country_directory_public_path(db: Session = Depends(get_db)):
    return jps.list_country_directory(db)
