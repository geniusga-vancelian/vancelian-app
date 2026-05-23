"""Progression d’inscription dérivée uniquement de ``profile_json.collected``.

- Pas de dépendance au curseur session (``current_step``) pour calculer la prochaine étape ni le %.
- Aligné sur les jalons utilisés dans ``registration_progress._completion_ratio`` (reg_keys).
- Compatible flux EU v3 (step_key = clé canonique) et v4 (modules : résolution via ``screen_key``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Ordre strict — premier jalon incomplet = prochaine étape logique
ORDERED_CANONICAL_KEYS: List[str] = [
    "identity",
    "date_of_birth",
    "residence_country",
    "home_address",
    "mobile_phone",
    "phone_verification",
    "contact_email",
    "email_verification_optional",
    "terms",
    "employment_status",
    "work_sector",
    "work_details",
    "annual_income",
    "net_worth",
    "source_of_wealth",
    "financial_acknowledgements",
]

# Écran runtime (EU v4) ; fallback possible sur step_key = clé canonique (v3)
CANONICAL_KEY_TO_SCREEN_KEY: Dict[str, str] = {
    "identity": "identity_form",
    "date_of_birth": "dob_form",
    "residence_country": "residence_country_form",
    "home_address": "home_address_form",
    "mobile_phone": "mobile_phone_form",
    "phone_verification": "phone_verification_sms",
    "contact_email": "email_form",
    "email_verification_optional": "email_otp_optional_form",
    "terms": "terms_form",
    "employment_status": "employment_status_form",
    "work_sector": "work_sector_form",
    "work_details": "work_details_form",
    "annual_income": "annual_income_form",
    "net_worth": "net_worth_form",
    "source_of_wealth": "source_of_wealth_form",
    "financial_acknowledgements": "financial_acknowledgements_form",
}

CANONICAL_LABELS_FR: Dict[str, str] = {
    "identity": "Identité et nom",
    "date_of_birth": "Date de naissance",
    "residence_country": "Pays de résidence",
    "home_address": "Adresse du domicile",
    "mobile_phone": "Numéro de mobile",
    "phone_verification": "Vérification mobile",
    "contact_email": "Adresse e-mail",
    "email_verification_optional": "Vérification e-mail",
    "terms": "Conditions générales",
    "employment_status": "Situation professionnelle",
    "work_sector": "Secteur d’activité",
    "work_details": "Poste et employeur",
    "annual_income": "Revenu annuel",
    "net_worth": "Patrimoine",
    "source_of_wealth": "Origine des fonds",
    "financial_acknowledgements": "Déclarations réglementaires",
}


def get_collected_value(collected: Any, slug: str, default: Any = None) -> Any:
    """Lit une valeur dans le mapping ``collected`` (niveau plat)."""
    if not isinstance(collected, dict):
        return default
    if slug in collected:
        return collected[slug]
    return default


def _nonempty(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, bool):
        return v
    return True


def _check_identity(c: Dict[str, Any]) -> bool:
    fn = get_collected_value(c, "first_name") or get_collected_value(c, "given_name")
    ln = get_collected_value(c, "last_name") or get_collected_value(c, "family_name")
    return _nonempty(fn) and _nonempty(ln)


def _check_dob(c: Dict[str, Any]) -> bool:
    return _nonempty(
        get_collected_value(c, "date_of_birth") or get_collected_value(c, "birth_date")
    )


def _check_residence(c: Dict[str, Any]) -> bool:
    return _nonempty(
        get_collected_value(c, "country_of_residence") or get_collected_value(c, "country")
    )


def _check_home_address(c: Dict[str, Any]) -> bool:
    if _nonempty(get_collected_value(c, "address_line_1")):
        return True
    return _nonempty(get_collected_value(c, "address_metadata"))


def _check_mobile_phone(c: Dict[str, Any]) -> bool:
    return _nonempty(
        get_collected_value(c, "phone_e164")
        or get_collected_value(c, "phone_number")
    )


def _check_phone_verification(c: Dict[str, Any]) -> bool:
    if get_collected_value(c, "phone_verified") is True:
        return True
    return _nonempty(get_collected_value(c, "phone_verified_at"))


def _check_contact_email(c: Dict[str, Any]) -> bool:
    return _nonempty(get_collected_value(c, "email"))


def _check_email_verification_optional(c: Dict[str, Any]) -> bool:
    if _nonempty(get_collected_value(c, "email_verification_code")):
        return True
    if get_collected_value(c, "email_verification_skipped") is True:
        return True
    return False


def _check_terms(c: Dict[str, Any]) -> bool:
    v = get_collected_value(c, "terms_accepted")
    if v is True or v == "true":
        return True
    v2 = get_collected_value(c, "terms_and_conditions")
    return v2 is True or v2 == "true"


def _check_employment_status(c: Dict[str, Any]) -> bool:
    return _nonempty(get_collected_value(c, "employment_status"))


def _check_work_sector(c: Dict[str, Any]) -> bool:
    """Écran dédié EU v125+ : secteur avant poste / employeur."""
    emp = get_collected_value(c, "employment_status")
    if emp not in ("employed", "self_employed"):
        return True
    return _nonempty(get_collected_value(c, "work_sector"))


def _check_work_details(c: Dict[str, Any]) -> bool:
    """Titres + employeur (le secteur est le jalon ``work_sector``)."""
    emp = get_collected_value(c, "employment_status")
    if emp not in ("employed", "self_employed"):
        return True
    if not _nonempty(get_collected_value(c, "job_title")):
        return False
    if emp == "employed":
        return _nonempty(get_collected_value(c, "employer_name"))
    return True


def _check_annual_income(c: Dict[str, Any]) -> bool:
    return _nonempty(get_collected_value(c, "annual_income_range"))


def _check_net_worth(c: Dict[str, Any]) -> bool:
    return _nonempty(get_collected_value(c, "net_worth_range"))


def _check_source_of_wealth(c: Dict[str, Any]) -> bool:
    v = get_collected_value(c, "source_of_wealth")
    return isinstance(v, list) and len(v) > 0


def _check_financial_acknowledgements(c: Dict[str, Any]) -> bool:
    for slug in ("info_true_and_accurate", "compliance_usage_ack", "not_us_person"):
        if get_collected_value(c, slug) is not True:
            return False
    return True


_CHECKERS: Dict[str, Any] = {
    "identity": _check_identity,
    "date_of_birth": _check_dob,
    "residence_country": _check_residence,
    "home_address": _check_home_address,
    "mobile_phone": _check_mobile_phone,
    "phone_verification": _check_phone_verification,
    "contact_email": _check_contact_email,
    "email_verification_optional": _check_email_verification_optional,
    "terms": _check_terms,
    "employment_status": _check_employment_status,
    "work_sector": _check_work_sector,
    "work_details": _check_work_details,
    "annual_income": _check_annual_income,
    "net_worth": _check_net_worth,
    "source_of_wealth": _check_source_of_wealth,
    "financial_acknowledgements": _check_financial_acknowledgements,
}


def is_canonical_step_complete(collected: Any, key: str) -> bool:
    """Indique si le jalon ``key`` est satisfait d’après ``collected`` seul."""
    if not isinstance(collected, dict):
        collected = {}
    fn = _CHECKERS.get(key)
    if fn is None:
        return False
    return bool(fn(collected))


def compute_registration_progress_from_collected(
    collected: Any,
) -> Tuple[float, int, int, int]:
    """Retourne (ratio 0..1, pourcentage 0..100, complétés, total).

    Total = nombre de jalons canoniques (len(ORDERED_CANONICAL_KEYS)).
    """
    done = sum(1 for k in ORDERED_CANONICAL_KEYS if is_canonical_step_complete(collected, k))
    total = len(ORDERED_CANONICAL_KEYS)
    if total == 0:
        return 0.0, 0, 0, 0
    ratio = round(done / float(total), 4)
    pct = min(100, int(round(ratio * 100)))
    return ratio, pct, done, total


def compute_next_registration_step_from_collected(
    collected: Any,
) -> Optional[Tuple[str, str]]:
    """Prochain jalon incomplet : (clé canonique, libellé FR). None si tout est complété."""
    if not isinstance(collected, dict):
        collected = {}
    for key in ORDERED_CANONICAL_KEYS:
        if not is_canonical_step_complete(collected, key):
            return (key, CANONICAL_LABELS_FR.get(key, key))
    return None


@dataclass(frozen=True)
class DerivedRegistrationProgress:
    completion_ratio: float
    progress_percent: int
    completed_count: int
    total_count: int
    next_step_key: Optional[str]
    next_step_label_fr: Optional[str]
    resume_description_fr: str


def build_derived_registration_progress(collected: Any) -> DerivedRegistrationProgress:
    ratio, pct, done, total = compute_registration_progress_from_collected(collected)
    nxt = compute_next_registration_step_from_collected(collected)
    if nxt is None:
        return DerivedRegistrationProgress(
            completion_ratio=ratio,
            progress_percent=pct,
            completed_count=done,
            total_count=total,
            next_step_key=None,
            next_step_label_fr=None,
            resume_description_fr="Votre dossier d’inscription est complet côté informations saisies.",
        )
    _k, label = nxt
    return DerivedRegistrationProgress(
        completion_ratio=ratio,
        progress_percent=pct,
        completed_count=done,
        total_count=total,
        next_step_key=nxt[0],
        next_step_label_fr=label,
        resume_description_fr=(
            "Quelques informations complémentaires permettent de finaliser votre compte. "
            f"Prochaine étape : {label}."
        ),
    )
