"""Tests for DB-driven jurisdiction policies (phone, residence, nationality).

Requires Alembic migration through ``103`` (``policy_scope`` on
``public.field_definitions`` + component props backfill). If tables or columns
are missing, tests are skipped.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from database import (
    CountryDirectory,
    JurisdictionCountryPolicy,
    JurisdictionPolicySettings,
    RegistrationJurisdiction,
)
from services.registration.jurisdiction_policies import (
    enrich_registration_component_props,
    list_allowed_nationality_countries,
    list_allowed_phone_countries,
    list_allowed_residence_countries,
)
from services.registration.jurisdiction_policy_submit import (
    validate_jurisdiction_policies_on_submit,
)
from services.registration.validators import validate_screen_answers
from services.registration.phone_validation import validate_mobile_phone_for_jurisdiction
from services.registration.service import ValidationError


def _policy_tables_ready(db: Session) -> bool:
    try:
        b = db.get_bind()
        insp = inspect(b)
        if not insp.has_table("country_directory", schema="public"):
            return False
        if not insp.has_table("jurisdiction_policy_settings", schema="public"):
            return False
        cols = {
            c["name"]
            for c in insp.get_columns("jurisdiction_country_policies", schema="public")
        }
        fd_cols = {
            c["name"]
            for c in insp.get_columns("field_definitions", schema="public")
        }
        return "allow_nationality" in cols and "policy_scope" in fd_cols
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _require_jurisdiction_country_tables(db: Session):
    if not _policy_tables_ready(db):
        pytest.skip(
            "Policy tables or policy_scope missing — run `alembic upgrade head` (103+) on the test database."
        )


def _phone_comp(slug: str = "phone_number") -> SimpleNamespace:
    return SimpleNamespace(
        binding_slug=slug,
        component_type="phone_input",
        props_json={"policy_scope": "phone"},
    )


def _country_comp(slug: str, scope: str) -> SimpleNamespace:
    return SimpleNamespace(
        binding_slug=slug,
        component_type="country_picker",
        props_json={"policy_scope": scope},
    )


def _address_step_comp() -> SimpleNamespace:
    return SimpleNamespace(
        binding_slug="address_line_1",
        component_type="address_step",
        props_json={},
    )


def _address_autocomplete_comp() -> SimpleNamespace:
    return SimpleNamespace(
        binding_slug="address_line_1",
        component_type="address_autocomplete",
        props_json={
            "binding_slugs": {
                "street": "address_line_1",
                "postal": "postal_code",
                "city": "city",
                "country": "country_of_residence",
            }
        },
    )


def _get_or_create_country(
    db: Session,
    *,
    iso2: str,
    iso3: str,
    dial: str,
    en: str,
    fr: str,
) -> CountryDirectory:
    row = db.query(CountryDirectory).filter(CountryDirectory.iso2 == iso2).first()
    if row:
        return row
    c = CountryDirectory(
        id=uuid.uuid4(),
        iso2=iso2,
        iso3=iso3,
        display_name_en=en,
        display_name_fr=fr,
        phone_country_code=dial,
        is_active=True,
    )
    db.add(c)
    db.flush()
    return c


def _ensure_registration_jurisdiction(db: Session, code: str, name: str) -> None:
    if (
        db.query(RegistrationJurisdiction)
        .filter(RegistrationJurisdiction.code == code)
        .first()
    ):
        return
    db.add(
        RegistrationJurisdiction(
            id=uuid.uuid4(),
            code=code,
            name=name,
            entity_name=name,
            default_language="en",
            is_active=True,
        )
    )
    db.flush()


def _add_policy(
    db: Session,
    jurisdiction_code: str,
    iso2: str,
    *,
    allow_residence: bool = True,
    allow_phone: bool = True,
    allow_nationality: bool = False,
    is_default_residence: bool = False,
    is_default_phone: bool = False,
    position: int = 0,
) -> None:
    exists = (
        db.query(JurisdictionCountryPolicy)
        .filter(
            JurisdictionCountryPolicy.jurisdiction_code == jurisdiction_code,
            JurisdictionCountryPolicy.country_iso2 == iso2,
        )
        .first()
    )
    if exists:
        return
    db.add(
        JurisdictionCountryPolicy(
            id=uuid.uuid4(),
            jurisdiction_code=jurisdiction_code,
            country_iso2=iso2,
            allow_residence=allow_residence,
            allow_phone_country_code=allow_phone,
            allow_nationality=allow_nationality,
            is_default_residence=is_default_residence,
            is_default_phone=is_default_phone,
            position=position,
        )
    )
    db.flush()


@pytest.fixture
def jcp_seed(db: Session):
    """Per-test jurisdiction codes: EU (FR+DE+US nat-only), UAE (AE res + FR nat)."""
    suf = uuid.uuid4().hex[:8].upper()
    jc_eu = f"JTEU{suf}"
    jc_uae = f"JTAE{suf}"
    _ensure_registration_jurisdiction(db, jc_eu, "Jurisdiction test EU")
    _ensure_registration_jurisdiction(db, jc_uae, "Jurisdiction test UAE")
    _get_or_create_country(
        db,
        iso2="FR",
        iso3="FRA",
        dial="+33",
        en="France",
        fr="France",
    )
    _get_or_create_country(
        db,
        iso2="DE",
        iso3="DEU",
        dial="+49",
        en="Germany",
        fr="Allemagne",
    )
    _get_or_create_country(
        db,
        iso2="AE",
        iso3="ARE",
        dial="+971",
        en="United Arab Emirates",
        fr="Émirats arabes unis",
    )
    _get_or_create_country(
        db,
        iso2="US",
        iso3="USA",
        dial="+1",
        en="United States",
        fr="États-Unis",
    )
    for iso2, pos, def_res, def_ph in [
        ("FR", 0, True, True),
        ("DE", 1, False, False),
    ]:
        _add_policy(
            db,
            jc_eu,
            iso2,
            allow_nationality=True,
            is_default_residence=def_res,
            is_default_phone=def_ph,
            position=pos,
        )
    _add_policy(
        db,
        jc_eu,
        "US",
        allow_residence=False,
        allow_phone=False,
        allow_nationality=True,
        position=2,
    )
    _add_policy(
        db,
        jc_uae,
        "AE",
        is_default_residence=True,
        is_default_phone=True,
        allow_nationality=True,
        position=0,
    )
    _add_policy(
        db,
        jc_uae,
        "FR",
        allow_residence=False,
        allow_phone=False,
        allow_nationality=True,
        position=1,
    )
    return {"eu": jc_eu, "uae": jc_uae}


def test_service_eu_lists_multiple_european_countries(db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    phone = list_allowed_phone_countries(db, jc)
    res = list_allowed_residence_countries(db, jc)
    nat = list_allowed_nationality_countries(db, jc)
    iso_phone = sorted(x["iso2"] for x in phone)
    iso_res = sorted(x["iso2"] for x in res)
    iso_nat = sorted(x["iso2"] for x in nat)
    assert iso_phone == ["DE", "FR"]
    assert iso_res == ["DE", "FR"]
    assert iso_nat == ["DE", "FR", "US"]


def test_service_uae_lists_ae_only_residence_fr_nat_wider(db: Session, jcp_seed):
    jc = jcp_seed["uae"]
    phone = list_allowed_phone_countries(db, jc)
    res = list_allowed_residence_countries(db, jc)
    nat = list_allowed_nationality_countries(db, jc)
    assert [x["iso2"] for x in phone] == ["AE"]
    assert [x["iso2"] for x in res] == ["AE"]
    assert sorted(x["iso2"] for x in nat) == ["AE", "FR"]


def test_enrich_phone_input_props(db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    props = {"label": "Phone", "required": True}
    out = enrich_registration_component_props(
        db, jc, "phone_input", props, "en", "en", None
    )
    assert "allowed_phone_countries" in out
    assert len(out["allowed_phone_countries"]) == 2
    assert out.get("default_phone_country") == "FR"


def test_enrich_country_picker_residence_binding(db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    props = {"label": "Country", "required": True}
    out = enrich_registration_component_props(
        db, jc, "country_picker", props, "en", "en", "country_of_residence"
    )
    assert "allowed_countries" in out
    assert len(out["allowed_countries"]) == 2
    assert out.get("default_country") == "FR"


def test_enrich_country_picker_legacy_slug_uses_residence(db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    out = enrich_registration_component_props(
        db, jc, "country_picker", {}, "en", "en", "custom_slug"
    )
    assert len(out.get("allowed_countries", [])) == 2


def test_enrich_country_picker_nationality_distinct_uae(db: Session, jcp_seed):
    jc = jcp_seed["uae"]
    out = enrich_registration_component_props(
        db, jc, "country_picker", {}, "en", "en", "nationality"
    )
    assert "allowed_countries" in out
    iso = sorted(c["iso2"] for c in out["allowed_countries"])
    assert iso == ["AE", "FR"]
    res_out = enrich_registration_component_props(
        db, jc, "country_picker", {}, "en", "en", "country_of_residence"
    )
    res_iso = [c["iso2"] for c in res_out["allowed_countries"]]
    assert res_iso == ["AE"]
    assert iso != res_iso


def test_inherit_phone_derives_from_residence(db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    pol_de = (
        db.query(JurisdictionCountryPolicy)
        .filter(
            JurisdictionCountryPolicy.jurisdiction_code == jc,
            JurisdictionCountryPolicy.country_iso2 == "DE",
        )
        .first()
    )
    assert pol_de is not None
    pol_de.allow_phone_country_code = False
    st = JurisdictionPolicySettings(
        id=uuid.uuid4(),
        jurisdiction_code=jc,
        inherit_phone_countries_from_residence=True,
        default_residence_iso2="FR",
        default_phone_iso2="FR",
    )
    db.add(st)
    db.flush()
    phone = list_allowed_phone_countries(db, jc)
    assert sorted(x["iso2"] for x in phone) == ["DE", "FR"]


def test_phone_country_mismatch_fr_number_de_selected(db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    r = validate_mobile_phone_for_jurisdiction(
        db,
        "+33612345678",
        jc,
        selected_country_iso2="DE",
        enforce_jurisdiction_allowlist=True,
    )
    assert not r.ok
    assert r.error_code == "phone_country_mismatch"


def test_submit_fr_phone_accepted_in_eu(db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    comps = [
        _phone_comp(),
    ]
    validate_jurisdiction_policies_on_submit(
        db,
        jc,
        comps,
        {"phone_number": "+33612345678", "phone_number_country_code": "FR"},
    )


def test_submit_fr_phone_raw_national_accepted_in_eu(db: Session, jcp_seed):
    """Structured submit: national input in phone_number_raw (no client-built E.164)."""
    jc = jcp_seed["eu"]
    comps = [
        _phone_comp(),
    ]
    answers = {
        "phone_number_raw": "0612345678",
        "phone_number_country_code": "FR",
    }
    validate_jurisdiction_policies_on_submit(db, jc, comps, answers)
    assert answers["phone_number"] == "+33612345678"


def test_submit_ae_phone_rejected_in_eu(db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    comps = [
        _phone_comp(),
    ]
    with pytest.raises(ValidationError) as ei:
        validate_jurisdiction_policies_on_submit(
            db,
            jc,
            comps,
            {"phone_number": "+971501234567", "phone_number_country_code": "AE"},
        )
    assert getattr(ei.value, "code", None) == "unsupported_phone_country"


def test_submit_971_accepted_in_uae(db: Session, jcp_seed):
    jc = jcp_seed["uae"]
    comps = [
        _phone_comp(),
    ]
    validate_jurisdiction_policies_on_submit(
        db,
        jc,
        comps,
        {"phone_number": "+971501234567", "phone_number_country_code": "AE"},
    )


def test_submit_residence_fr_rejected_in_uae(db: Session, jcp_seed):
    jc = jcp_seed["uae"]
    comps = [
        _country_comp("country_of_residence", "residence"),
    ]
    with pytest.raises(ValidationError) as ei:
        validate_jurisdiction_policies_on_submit(
            db,
            jc,
            comps,
            {"country_of_residence": "FR"},
        )
    assert "[RESIDENCE_COUNTRY_NOT_ALLOWED]" in str(ei.value)


def test_submit_residence_fr_rejected_in_uae_address_step(db: Session, jcp_seed):
    """Residence policy applies to country bound via address_step (not only country_picker)."""
    jc = jcp_seed["uae"]
    with pytest.raises(ValidationError) as ei:
        validate_jurisdiction_policies_on_submit(
            db,
            jc,
            [_address_step_comp()],
            {"country_of_residence": "FR"},
        )
    assert "[RESIDENCE_COUNTRY_NOT_ALLOWED]" in str(ei.value)


def test_submit_residence_ae_accepted_in_uae_address_step(db: Session, jcp_seed):
    jc = jcp_seed["uae"]
    validate_jurisdiction_policies_on_submit(
        db,
        jc,
        [_address_step_comp()],
        {"country_of_residence": "AE"},
    )


def test_submit_residence_fr_rejected_in_uae_address_autocomplete(db: Session, jcp_seed):
    jc = jcp_seed["uae"]
    with pytest.raises(ValidationError) as ei:
        validate_jurisdiction_policies_on_submit(
            db,
            jc,
            [_address_autocomplete_comp()],
            {"country_of_residence": "FR"},
        )
    assert "[RESIDENCE_COUNTRY_NOT_ALLOWED]" in str(ei.value)


def test_validate_screen_answers_address_step_country_must_be_iso2():
    comp = SimpleNamespace(
        binding_slug="address_line_1",
        component_type="address_step",
        props_json={},
    )
    errs = validate_screen_answers(
        [comp],
        {"country_of_residence": "FRA", "address_line_1": "1 rue"},
    )
    assert any(e.slug == "country_of_residence" for e in errs)


def test_validate_screen_answers_address_autocomplete_country_must_be_iso2():
    comp = SimpleNamespace(
        binding_slug="address_line_1",
        component_type="address_autocomplete",
        props_json={},
    )
    errs = validate_screen_answers(
        [comp],
        {"country_of_residence": "999", "address_line_1": "x"},
    )
    assert any(e.slug == "country_of_residence" for e in errs)


def test_submit_residence_ae_accepted_in_uae(db: Session, jcp_seed):
    jc = jcp_seed["uae"]
    comps = [
        _country_comp("country_of_residence", "residence"),
    ]
    validate_jurisdiction_policies_on_submit(
        db,
        jc,
        comps,
        {"country_of_residence": "AE"},
    )


def test_submit_nationality_fr_accepted_in_uae(db: Session, jcp_seed):
    jc = jcp_seed["uae"]
    comps = [
        _country_comp("nationality", "nationality"),
    ]
    validate_jurisdiction_policies_on_submit(
        db,
        jc,
        comps,
        {"nationality": "FR"},
    )


def test_submit_nationality_us_rejected_in_uae(db: Session, jcp_seed):
    jc = jcp_seed["uae"]
    comps = [
        _country_comp("nationality", "nationality"),
    ]
    with pytest.raises(ValidationError) as ei:
        validate_jurisdiction_policies_on_submit(
            db,
            jc,
            comps,
            {"nationality": "US"},
        )
    assert "[NATIONALITY_COUNTRY_NOT_ALLOWED]" in str(ei.value)


def test_submit_residence_us_rejected_nationality_us_ok_eu(db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    comps = [
        _country_comp("country_of_residence", "residence"),
        _country_comp("nationality", "nationality"),
    ]
    with pytest.raises(ValidationError) as ei:
        validate_jurisdiction_policies_on_submit(
            db,
            jc,
            comps,
            {"country_of_residence": "US", "nationality": "US"},
        )
    assert "[RESIDENCE_COUNTRY_NOT_ALLOWED]" in str(ei.value)

    validate_jurisdiction_policies_on_submit(
        db,
        jc,
        [comps[1]],
        {"nationality": "US"},
    )


def test_admin_get_country_policies(client, db: Session, jcp_seed):
    r = client.get(f"/api/admin/jurisdictions/{jcp_seed['eu']}/country-policies")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    codes = sorted(row["country_iso2"] for row in data)
    assert codes == ["DE", "FR", "US"]
    assert all("allow_nationality" in row for row in data)


def test_admin_list_jurisdiction_policies(client, db: Session, jcp_seed):
    r = client.get("/api/admin/jurisdiction-policies")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    codes = {r["code"] for r in rows}
    assert jcp_seed["eu"] in codes


def test_admin_get_jurisdiction_policy_detail(client, db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    r = client.get(f"/api/admin/jurisdiction-policies/{jc}")
    assert r.status_code == 200
    body = r.json()
    assert body["jurisdiction"]["code"] == jc
    assert len(body["countries"]) == 3
    assert body["summary"]["nationality_country_count"] == 3


def test_admin_patch_countries_persists_allow_nationality(client, db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    r = client.patch(
        f"/api/admin/jurisdiction-policies/{jc}/countries",
        json={
            "rows": [
                {
                    "country_iso2": "FR",
                    "allow_residence": True,
                    "allow_phone_country_code": True,
                    "allow_nationality": True,
                    "is_default_residence": True,
                    "is_default_phone": True,
                    "position": 0,
                },
                {
                    "country_iso2": "DE",
                    "allow_residence": True,
                    "allow_phone_country_code": True,
                    "allow_nationality": False,
                    "is_default_residence": False,
                    "is_default_phone": False,
                    "position": 1,
                },
            ]
        },
    )
    assert r.status_code == 200
    de = next(c for c in r.json()["countries"] if c["country_iso2"] == "DE")
    assert de["allow_nationality"] is False


def test_admin_patch_countries_rejects_two_default_residence(client, db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    r = client.patch(
        f"/api/admin/jurisdiction-policies/{jc}/countries",
        json={
            "rows": [
                {
                    "country_iso2": "FR",
                    "allow_residence": True,
                    "allow_phone_country_code": True,
                    "allow_nationality": True,
                    "is_default_residence": True,
                    "is_default_phone": True,
                    "position": 0,
                },
                {
                    "country_iso2": "DE",
                    "allow_residence": True,
                    "allow_phone_country_code": True,
                    "allow_nationality": True,
                    "is_default_residence": True,
                    "is_default_phone": False,
                    "position": 1,
                },
            ]
        },
    )
    assert r.status_code == 422


def test_admin_apply_preset_clear(client, db: Session, jcp_seed):
    jc = jcp_seed["eu"]
    r = client.post(
        f"/api/admin/jurisdiction-policies/{jc}/apply-preset",
        json={"preset": "clear"},
    )
    assert r.status_code == 200
    assert r.json()["countries"] == []


def test_runtime_uae_ae_only_when_seeded(db: Session):
    if not db.query(JurisdictionCountryPolicy).filter_by(jurisdiction_code="UAE").first():
        pytest.skip("UAE policy not seeded")
    phone = list_allowed_phone_countries(db, "UAE")
    assert [x["iso2"] for x in phone] == ["AE"]
