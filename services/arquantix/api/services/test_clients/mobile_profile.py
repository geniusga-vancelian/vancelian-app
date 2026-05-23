"""Projection profil mobile (person.profile_json → initiales + sections Mon compte)."""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from database import AdminUser, Person
from services.portfolio_engine.clients.models import Client
from services.customers_admin.registration_progress import (
    compute_canonical_registration_progress,
)
from services.registration_progress_derived import build_derived_registration_progress
from services.registration.service import get_person_collected_value
from services.test_clients.security_preferences_v1 import (
    build_security_preferences_read_dict,
    security_blob_from_person,
)

logger = logging.getLogger(__name__)

def security_preferences_dict(person: Optional[Person]) -> dict[str, Any]:
    """Lecture ``profile_json.security`` — modèle V1 structuré + legacy dérivé (jamais vérité legacy seule)."""
    if person is None:
        return build_security_preferences_read_dict({})
    return build_security_preferences_read_dict(security_blob_from_person(person.profile_json))


def load_person_for_client(db: Session, client: Client) -> Optional[Person]:
    if not client.person_id:
        return None
    return db.query(Person).filter(Person.id == client.person_id).first()


def sync_pe_client_email_from_collected(db: Session, client: Client) -> Client:
    """Si ``pe_clients.email`` est vide et que le profil a un e-mail dans ``collected``, aligner ``pe_clients.email``."""
    if not client.person_id:
        return client
    ce = getattr(client, "email", None)
    if ce and str(ce).strip():
        return client
    person = load_person_for_client(db, client)
    if person is None:
        return client
    raw = get_person_collected_value(person, "email")
    if raw is None:
        raw = get_person_collected_value(person, "contact_email")
    if raw is None:
        return client
    real = str(raw).strip()
    if not real or "@" not in real:
        return client
    # Unicité pe_clients.email
    taken = (
        db.query(Client)
        .filter(Client.email == real, Client.id != client.id)
        .first()
    )
    if taken is not None:
        logger.warning(
            "mobile_profile: skip pe_clients email sync — %r already bound to another client",
            real[:48],
        )
        return client
    client.email = real
    db.flush()
    db.refresh(client)
    logger.info("mobile_profile: synced pe_clients.email from collected for client_id=%s", client.id)
    return client


def _resolve_display_email(db: Session, person: Optional[Person], client: Client) -> str:
    """E-mail affiché : ``collected`` en priorité, puis ``pe_clients.email``, puis ``admin_users.email``."""
    ce = _first_collected(person, ("email", "contact_email")) if person else None
    if ce and "@" in ce:
        return ce.strip()
    if client.email and str(client.email).strip() and "@" in str(client.email):
        return str(client.email).strip()
    if person:
        u = db.query(AdminUser).filter(AdminUser.person_id == person.id).first()
        if u and u.email and str(u.email).strip() and "@" in str(u.email):
            return str(u.email).strip()
    return ""


def _phone_for_contact(
    db: Session, person: Optional[Person], collected_phone: Optional[str],
) -> Optional[str]:
    if collected_phone:
        return collected_phone
    if person is None:
        return None
    u = db.query(AdminUser).filter(AdminUser.person_id == person.id).first()
    if u is None or not getattr(u, "mobile_e164", None):
        return None
    return str(u.mobile_e164).strip() or None


def _s(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        t = v.strip()
        return t or None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(v).strip() or None
    if isinstance(v, bool):
        return "Oui" if v else "Non"
    return str(v).strip() or None


def _bool_display(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, bool):
        return "Oui" if v else "Non"
    if isinstance(v, str):
        ls = v.strip().lower()
        if ls in ("true", "1", "yes", "oui"):
            return "Oui"
        if ls in ("false", "0", "no", "non"):
            return "Non"
        return v.strip() or None
    return None


def _list_display(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, list):
        parts = [_s(x) for x in v]
        parts = [p for p in parts if p]
        if not parts:
            return None
        return ", ".join(parts)
    return _s(v)


def _first_collected(person: Optional[Person], slugs: tuple[str, ...]) -> Optional[str]:
    if person is None:
        return None
    for slug in slugs:
        val = get_person_collected_value(person, slug)
        out = _s(val)
        if out:
            return out
    return None


_EMPLOYMENT_STATUS_FR: dict[str, str] = {
    "employed": "Salarié",
    "self_employed": "Indépendant / libéral",
    "student": "Étudiant",
    "retired": "Retraité",
    "unemployed": "Sans emploi",
    "homemaker": "Au foyer",
    "other": "Autre",
}


def _employment_status_display(raw: Optional[str]) -> Optional[str]:
    if not raw or not isinstance(raw, str):
        return None
    key = raw.strip().lower()
    return _EMPLOYMENT_STATUS_FR.get(key, raw.strip())


def _extract_address_line1_from_metadata(person: Optional[Person]) -> Optional[str]:
    if person is None:
        return None
    am = get_person_collected_value(person, "address_metadata")
    if not isinstance(am, dict):
        return None
    fa = am.get("formatted_address")
    if isinstance(fa, str) and fa.strip():
        return fa.strip()
    # Repli : champs fréquents Places / manuel
    for k in ("street", "line1", "address_line_1", "route"):
        v = am.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def build_initials(*, client_email: Optional[str], person: Optional[Person]) -> str:
    if person is not None:
        fn = _first_collected(person, ("first_name", "given_name", "firstname"))
        ln = _first_collected(person, ("last_name", "family_name", "surname"))
        if fn and ln:
            return (fn[0] + ln[0]).upper()
        if fn and len(fn) >= 2:
            return fn[:2].upper()
        if fn:
            return (fn[0] + (fn[-1] if len(fn) > 1 else fn[0])).upper()
    local = (client_email or "").split("@", 1)[0].strip()
    segs = [x for x in re.split(r"[._\-\s]+", local) if x and x.isalpha()]
    if len(segs) >= 2:
        return (segs[0][0] + segs[1][0]).upper()
    alnum = "".join(c for c in local if c.isalnum())
    if len(alnum) >= 2:
        return alnum[:2].upper()
    if len(alnum) == 1:
        return (alnum * 2).upper()
    return "?"


def _mask_doc_number(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    t = raw.replace(" ", "").strip()
    if len(t) <= 4:
        return "••••"
    return "•••• •••• " + t[-4:]


def build_mobile_profile_dict(db: Session, client: Client) -> dict[str, Any]:
    client = sync_pe_client_email_from_collected(db, client)
    person = load_person_for_client(db, client)
    display_email = _resolve_display_email(db, person, client)
    initials = build_initials(client_email=display_email, person=person)

    first_name = _first_collected(person, ("first_name", "given_name", "firstname"))
    last_name = _first_collected(person, ("last_name", "family_name", "surname"))
    date_of_birth = _first_collected(
        person, ("date_of_birth", "birth_date", "dob", "date_of_birth_iso")
    )
    nationality = _first_collected(person, ("nationality", "nationality_label"))

    line1 = _first_collected(
        person, ("address_line_1", "street_address", "street", "address")
    )
    if not line1:
        line1 = _extract_address_line1_from_metadata(person)

    line2 = _first_collected(person, ("address_line_2", "address_complement", "complement"))
    postal = _first_collected(person, ("postal_code", "zip", "zip_code"))
    city = _first_collected(person, ("city", "locality"))
    country = _first_collected(
        person,
        (
            "country_of_residence",
            "country",
            "residence_country",
        ),
    )

    doc_type = _first_collected(
        person, ("id_document_type", "document_type", "identity_document_type")
    )
    doc_num = _first_collected(
        person, ("id_document_number", "document_number", "identity_document_number")
    )
    doc_exp = _first_collected(
        person, ("id_document_expiry", "document_expiry", "id_document_expiry_date")
    )

    phone = _phone_for_contact(
        db,
        person,
        _first_collected(
            person,
            (
                "phone_e164",
                "mobile_e164",
                "phone_number",
                "mobile_phone",
                "national_phone_number",
            ),
        ),
    )

    personal = None
    pd = {
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": date_of_birth,
        "nationality": nationality,
    }
    pd = {k: v for k, v in pd.items() if v}
    if pd:
        personal = pd

    address = None
    ad = {
        "line1": line1,
        "line2": line2,
        "postal_code": postal,
        "city": city,
        "country": country,
    }
    ad = {k: v for k, v in ad.items() if v}
    if ad:
        address = ad

    identity = None
    masked = _mask_doc_number(doc_num)
    idict = {
        "document_type": doc_type,
        "document_number_masked": masked,
        "document_expiry": doc_exp,
    }
    idict = {k: v for k, v in idict.items() if v}
    if idict:
        identity = idict

    contact_email = display_email
    contact = None
    cd = {"email": contact_email, "phone": phone}
    cd = {k: v for k, v in cd.items() if v}
    if cd:
        contact = cd

    # --- Inscription (profil financier / pro / légal) — même source que registration_progress ---
    emp_raw = get_person_collected_value(person, "employment_status") if person else None
    emp_status: Optional[str] = None
    if isinstance(emp_raw, str) and emp_raw.strip():
        emp_status = _employment_status_display(emp_raw.strip())
    elif emp_raw is not None and not isinstance(emp_raw, (dict, list)):
        emp_status = _s(emp_raw)
    job_title = _first_collected(person, ("job_title",))
    work_sector = _first_collected(person, ("work_sector",))
    employer_name = _first_collected(person, ("employer_name", "company_name"))

    employment = None
    ed = {
        "employment_status": emp_status,
        "job_title": job_title,
        "work_sector": work_sector,
        "employer_name": employer_name,
    }
    ed = {k: v for k, v in ed.items() if v}
    if ed:
        employment = ed

    sow = _list_display(get_person_collected_value(person, "source_of_wealth")) if person else None
    financial = None
    fd = {
        "annual_income_range": _first_collected(person, ("annual_income_range",)),
        "net_worth_range": _first_collected(person, ("net_worth_range",)),
        "source_of_wealth": sow,
    }
    fd = {k: v for k, v in fd.items() if v}
    if fd:
        financial = fd

    legal = None
    ld = {
        "terms_accepted": _bool_display(get_person_collected_value(person, "terms_accepted"))
        if person
        else None,
        "info_true_and_accurate": _bool_display(
            get_person_collected_value(person, "info_true_and_accurate")
        )
        if person
        else None,
        "compliance_usage_ack": _bool_display(
            get_person_collected_value(person, "compliance_usage_ack")
        )
        if person
        else None,
        "not_us_person": _bool_display(get_person_collected_value(person, "not_us_person"))
        if person
        else None,
    }
    # terms_and_conditions (EU) peut être bool ou acceptation alternative
    if person and ld.get("terms_accepted") is None:
        v = get_person_collected_value(person, "terms_and_conditions")
        ld["terms_accepted"] = _bool_display(v)

    ld = {k: v for k, v in ld.items() if v}
    if ld:
        legal = ld

    jurisdiction = (person.jurisdiction or "").strip() if person else None
    if not jurisdiction:
        jurisdiction = None

    out: dict[str, Any] = {
        "initials": initials,
        "email": display_email,
        "personal": personal,
        "address": address,
        "identity": identity,
        "contact": contact,
        "employment": employment,
        "financial": financial,
        "legal": legal,
        "jurisdiction": jurisdiction,
        "kyc_status": getattr(client, "kyc_status", None),
        "client_status": getattr(client, "status", None),
        "reference_currency": getattr(client, "reference_currency", None),
    }

    if person is not None:
        try:
            block = compute_canonical_registration_progress(db, person, client)
            out["registration_completion_ratio"] = float(block.completion_ratio)
            out["registration_macro_stage"] = block.stage.value
            out["registration_macro_label"] = block.label
            out["registration_missing_steps"] = list(block.missing_steps)[:16]
            out["registration_completed_steps"] = list(block.completed_steps)[:16]
            snap = block.session_snapshot
            if snap is not None:
                out["registration_session_progress_percent"] = snap.progress_percent
                out["registration_session_current_step_key"] = snap.current_step_key
                out["registration_session_current_screen_key"] = snap.current_screen_key
        except Exception as exc:  # noqa: BLE001
            logger.warning("mobile_profile: registration_progress skipped: %s", exc)

        try:
            pj = person.profile_json or {}
            collected = pj.get("collected")
            if not isinstance(collected, dict):
                collected = {}
            derived = build_derived_registration_progress(collected)
            out["registration_derived_completion_ratio"] = derived.completion_ratio
            out["registration_derived_progress_percent"] = derived.progress_percent
            out["registration_derived_next_step_key"] = derived.next_step_key
            out["registration_derived_next_step_label"] = derived.next_step_label_fr
            out["registration_derived_resume_description"] = derived.resume_description_fr
            out["registration_derived_completed_count"] = derived.completed_count
            out["registration_derived_total_count"] = derived.total_count
        except Exception as exc:  # noqa: BLE001
            logger.warning("mobile_profile: registration_derived skipped: %s", exc)

        try:
            from services.activation_journey import build_activation_journey

            out["activation_journey"] = build_activation_journey(
                db, person=person, client=client, profile_dict=out
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("mobile_profile: activation_journey skipped: %s", exc)

        out["security_preferences"] = security_preferences_dict(person)
        pj_change = (person.profile_json or {}).get("contact_email_change")
        if isinstance(pj_change, dict) and pj_change:
            out["contact_email_change"] = {
                k: pj_change.get(k)
                for k in ("pending_email", "status", "requested_at", "confirmed_at")
                if pj_change.get(k) is not None
            }

    return out
