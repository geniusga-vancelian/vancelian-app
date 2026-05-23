"""Progression d’inscription — modèle canonique backend (foundation / registration / lifecycle).

Le ratio et les listes completed/missing sont calculés ici uniquement (pas de recalcul frontend).

Source of truth (résumé) :
- **registration_sessions (dernière par ``updated_at``)** : snapshot runtime (écran courant, statut).
- **Au moins une session ``completed``** : l’inscription moteur a été menée à terme — les jalons
  registration passent à « complété » même si une **nouvelle** session incomplète a été ouverte après coup.
- **profile_json.collected** : vérité persistée ; complète les jalons si la session courante ne les a pas encore marqués.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from database import (
    Person,
    RegistrationSession,
    RegistrationSessionStep,
    TwoFactorChallenge,
)
from services.portfolio_engine.clients.models import Client as PeClient
from services.registration.service import get_person_collected_value

from .schemas import (
    FoundationState,
    LifecycleState,
    RegistrationMacroStage,
    RegistrationProgressBlock,
    RegistrationProgressStage,
    RegistrationSessionSnapshot,
    RegistrationStateFlags,
)

# KYC : aligné sur client_identity.VALID_KYC_STATUSES + legacy "verified"
_KYC_DONE = frozenset({"approved", "verified"})
_KYC_REJECTED = frozenset({"rejected", "failed"})

# Signal serveur **optionnel** : défini si le client appelle ``POST /auth/security/local-passcode-ack``.
# Ne pas confondre avec un passcode stocké localement (secure storage).
_SERVER_PASSCODE_ACK_KEY = "local_passcode_registered_at"

_MACRO_LABELS_FR: Dict[RegistrationMacroStage, str] = {
    RegistrationMacroStage.PHONE_STARTED: "Téléphone renseigné",
    RegistrationMacroStage.ACCOUNT_SECURED: "Compte sécurisé (mobile vérifié)",
    RegistrationMacroStage.REGISTRATION_IN_PROGRESS: "Inscription en cours",
    RegistrationMacroStage.KYC_PENDING: "KYC à compléter ou en cours",
    RegistrationMacroStage.KYC_COMPLETED: "KYC validé",
    RegistrationMacroStage.PE_CLIENT_LINKED: "Compte portefeuille lié",
    RegistrationMacroStage.ACTIVE_CLIENT: "Client actif",
}

_ACCOUNT_SECURED_WITH_PASSCODE_ACK_FR = "Compte sécurisé (mobile + PIN enregistré)"


def _macro_label(macro: RegistrationMacroStage, foundation: FoundationState) -> str:
    if macro == RegistrationMacroStage.ACCOUNT_SECURED and foundation.passcode_created is True:
        return _ACCOUNT_SECURED_WITH_PASSCODE_ACK_FR
    return _MACRO_LABELS_FR[macro]


def _nonempty(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, bool):
        return v
    return True


def _person_has_phone(person: Person) -> bool:
    for slug in (
        "phone_e164",
        "national_phone_number",
        "phone",
        "mobile_e164",
        "mobile_phone",
    ):
        if _nonempty(get_person_collected_value(person, slug)):
            return True
    return False


def _passcode_server_signal(person: Person) -> Optional[bool]:
    """Signal serveur explicite uniquement — pas d’inférence depuis des clés locales non fiables.

    - ``True`` : ``profile_json.security.local_passcode_registered_at`` est présent (horodatage serveur).
    - ``None`` : aucun signal fiable (passcode 100 %% local possible — cas nominal).
    - ``False`` : réservé si un endpoint marque explicitement l’absence (peu utilisé).
    """
    pj = person.profile_json or {}
    sec = pj.get("security")
    if not isinstance(sec, dict):
        return None
    ts = sec.get(_SERVER_PASSCODE_ACK_KEY)
    if ts is not None and str(ts).strip():
        return True
    if sec.get("local_passcode_ack") is False:
        return False
    return None


def _has_verified_sms_challenge(db: Session, person_id: UUID) -> bool:
    return (
        db.query(TwoFactorChallenge)
        .filter(
            TwoFactorChallenge.person_id == person_id,
            TwoFactorChallenge.status == "verified",
            TwoFactorChallenge.channel.ilike("%sms%"),
        )
        .first()
        is not None
    )


def _jurisdiction_resolved(person: Person) -> bool:
    return bool((person.jurisdiction or "").strip())


def _latest_registration_session(db: Session, person_id: UUID) -> Optional[RegistrationSession]:
    """Dernière session par ``updated_at`` (vérité runtime actuelle)."""
    return (
        db.query(RegistrationSession)
        .options(
            joinedload(RegistrationSession.current_step),
            joinedload(RegistrationSession.current_screen),
            joinedload(RegistrationSession.step_states).joinedload(RegistrationSessionStep.step),
        )
        .filter(RegistrationSession.person_id == person_id)
        .order_by(RegistrationSession.updated_at.desc())
        .first()
    )


def _has_any_completed_registration_session(db: Session, person_id: UUID) -> bool:
    """True si au moins une session d’inscription est en ``completed`` (historique)."""
    return (
        db.query(RegistrationSession.id)
        .filter(
            RegistrationSession.person_id == person_id,
            RegistrationSession.status == "completed",
        )
        .first()
        is not None
    )


def _step_states_by_key(session: RegistrationSession) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for ss in session.step_states or []:
        if ss.step and ss.step.step_key:
            out[ss.step.step_key] = (ss.status or "").lower()
    return out


def _profile_identity(person: Person) -> bool:
    fn = get_person_collected_value(person, "first_name") or get_person_collected_value(
        person, "given_name"
    )
    ln = get_person_collected_value(person, "last_name") or get_person_collected_value(
        person, "family_name"
    )
    return _nonempty(fn) and _nonempty(ln)


def _profile_dob(person: Person) -> bool:
    return _nonempty(
        get_person_collected_value(person, "date_of_birth")
        or get_person_collected_value(person, "birth_date")
    )


def _profile_residence(person: Person) -> bool:
    return _nonempty(
        get_person_collected_value(person, "country_of_residence")
        or get_person_collected_value(person, "country")
    )


def _profile_address(person: Person) -> bool:
    if _nonempty(get_person_collected_value(person, "address_line_1")):
        return True
    if _nonempty(get_person_collected_value(person, "address_metadata")):
        return True
    return False


def _profile_email(person: Person) -> bool:
    return _nonempty(get_person_collected_value(person, "email"))


def _profile_terms(person: Person) -> bool:
    v = get_person_collected_value(person, "terms_accepted")
    return v is True or v == "true"


def _profile_employment_status(person: Person) -> bool:
    return _nonempty(get_person_collected_value(person, "employment_status"))


def _profile_work_sector(person: Person) -> bool:
    """Écran secteur (EU v125+) — avant poste / employeur."""
    emp = get_person_collected_value(person, "employment_status")
    if emp not in ("employed", "self_employed"):
        return True
    return _nonempty(get_person_collected_value(person, "work_sector"))


def _profile_work_details(person: Person) -> bool:
    """Si emploi / indépendant : titres + employeur si salarié (secteur = jalon ``work_sector``)."""
    emp = get_person_collected_value(person, "employment_status")
    if emp not in ("employed", "self_employed"):
        return True
    if not _nonempty(get_person_collected_value(person, "job_title")):
        return False
    if emp == "employed":
        return _nonempty(get_person_collected_value(person, "employer_name"))
    return True


def _profile_annual_income(person: Person) -> bool:
    return _nonempty(get_person_collected_value(person, "annual_income_range"))


def _profile_net_worth(person: Person) -> bool:
    return _nonempty(get_person_collected_value(person, "net_worth_range"))


def _profile_source_of_wealth(person: Person) -> bool:
    v = get_person_collected_value(person, "source_of_wealth")
    return isinstance(v, list) and len(v) > 0


def _profile_financial_acknowledgements(person: Person) -> bool:
    for slug in ("info_true_and_accurate", "compliance_usage_ack", "not_us_person"):
        if get_person_collected_value(person, slug) is not True:
            return False
    return True


def _profile_identity_foundation_complete(person: Person) -> bool:
    """Module EU v4 : fondation = identity → terms (écrans regroupés)."""
    return (
        _profile_identity(person)
        and _profile_dob(person)
        and _profile_residence(person)
        and _profile_address(person)
        and _profile_email(person)
        and _profile_email_optional_addressed(person)
        and _profile_terms(person)
    )


def _profile_financial_profile_module_complete(person: Person) -> bool:
    """Module EU v4 : financial_profile regroupe les sous-parties (secteur + détails + …)."""
    return (
        _profile_employment_status(person)
        and _profile_work_sector(person)
        and _profile_work_details(person)
        and _profile_annual_income(person)
        and _profile_net_worth(person)
        and _profile_source_of_wealth(person)
        and _profile_financial_acknowledgements(person)
    )


def _profile_email_optional_addressed(person: Person) -> bool:
    if _nonempty(get_person_collected_value(person, "email_verification_code")):
        return True
    if get_person_collected_value(person, "email_verification_skipped") is True:
        return True
    return False


def _step_done(states: Dict[str, str], key: str) -> bool:
    return states.get(key) in ("completed", "skipped")


def _registration_flags_with_source_priority(
    db: Session,
    person: Person,
    session: Optional[RegistrationSession],
) -> Tuple[Dict[str, bool], bool]:
    """Règle : **au moins une session completed** OU étapes de la dernière session ∪ profil.

    - ``registration_completed`` : toute session historique en ``completed`` (ne pas « oublier » une inscription
      terminée parce qu’une nouvelle session incomplète est plus récente).
    - Snapshot runtime : toujours la **dernière** session (voir ``_latest_registration_session``).
    """
    reg_completed_any = _has_any_completed_registration_session(db, person.id)
    states = _step_states_by_key(session) if session else {}

    def pick(key: str, profile_fn) -> bool:
        if reg_completed_any:
            return True
        if session is not None and _step_done(states, key):
            return True
        return profile_fn(person)

    flags = {
        "identity": pick("identity", _profile_identity),
        "date_of_birth": pick("date_of_birth", _profile_dob),
        "residence_country": pick("residence_country", _profile_residence),
        "home_address": pick("home_address", _profile_address),
        "contact_email": pick("contact_email", _profile_email),
        "email_verification_optional": pick(
            "email_verification_optional",
            _profile_email_optional_addressed,
        ),
        "terms": pick("terms", _profile_terms),
        "employment_status": pick("employment_status", _profile_employment_status),
        "work_sector": pick("work_sector", _profile_work_sector),
        "work_details": pick("work_details", _profile_work_details),
        "annual_income": pick("annual_income", _profile_annual_income),
        "net_worth": pick("net_worth", _profile_net_worth),
        "source_of_wealth": pick("source_of_wealth", _profile_source_of_wealth),
        "financial_acknowledgements": pick(
            "financial_acknowledgements",
            _profile_financial_acknowledgements,
        ),
        "identity_foundation": pick(
            "identity_foundation",
            _profile_identity_foundation_complete,
        ),
        "financial_profile": pick(
            "financial_profile",
            _profile_financial_profile_module_complete,
        ),
    }
    if reg_completed_any:
        flags["email_verification_optional"] = True

    return flags, reg_completed_any


def _kyc_raw(person: Person) -> str:
    return (person.kyc_status or "not_started").lower().strip()


def _lifecycle_flags(
    person: Person,
    pe: Optional[PeClient],
    *,
    registration_completed: bool,
) -> LifecycleState:
    """kyc_pending = inscription (moteur) terminée et KYC pas encore validé (hors rejet terminal)."""
    k = _kyc_raw(person)
    kyc_completed = k in _KYC_DONE
    kyc_rejected = k in _KYC_REJECTED

    pe_linked = pe is not None
    active = pe is not None and (pe.status or "").lower() == "active"

    kyc_pending = (
        registration_completed
        and not kyc_completed
        and not kyc_rejected
    )

    return LifecycleState(
        kyc_pending=kyc_pending,
        kyc_completed=kyc_completed,
        pe_client_linked=pe_linked,
        active_client=active,
    )


def _macro_from_signals(
    *,
    person: Person,
    foundation: FoundationState,
    reg_completed: bool,
    lifecycle: LifecycleState,
    session: Optional[RegistrationSession],
) -> RegistrationMacroStage:
    """Priorité : PE → KYC validé → KYC à faire (post-inscription) → inscription → fondation."""
    if lifecycle.active_client:
        return RegistrationMacroStage.ACTIVE_CLIENT
    if lifecycle.pe_client_linked:
        return RegistrationMacroStage.PE_CLIENT_LINKED
    if lifecycle.kyc_completed:
        return RegistrationMacroStage.KYC_COMPLETED
    if reg_completed and _kyc_raw(person) in _KYC_REJECTED:
        return RegistrationMacroStage.KYC_PENDING
    if lifecycle.kyc_pending:
        return RegistrationMacroStage.KYC_PENDING
    if session is not None and session.status != "completed":
        return RegistrationMacroStage.REGISTRATION_IN_PROGRESS
    if foundation.mobile_verified and foundation.mobile_collected:
        return RegistrationMacroStage.ACCOUNT_SECURED
    if foundation.mobile_collected:
        return RegistrationMacroStage.PHONE_STARTED
    return RegistrationMacroStage.PHONE_STARTED


def _legacy_stage(macro: RegistrationMacroStage) -> RegistrationProgressStage:
    if macro == RegistrationMacroStage.ACTIVE_CLIENT:
        return RegistrationProgressStage.ACTIVE_CLIENT
    if macro == RegistrationMacroStage.PE_CLIENT_LINKED:
        return RegistrationProgressStage.PE_CLIENT_LINKED
    if macro == RegistrationMacroStage.KYC_COMPLETED:
        return RegistrationProgressStage.KYC_APPROVED
    if macro == RegistrationMacroStage.KYC_PENDING:
        return RegistrationProgressStage.KYC_PENDING
    if macro == RegistrationMacroStage.REGISTRATION_IN_PROGRESS:
        return RegistrationProgressStage.REGISTRATION_ACTIVE
    if macro == RegistrationMacroStage.ACCOUNT_SECURED:
        return RegistrationProgressStage.PROFILE_PARTIAL
    return RegistrationProgressStage.PHONE_STARTED


def _completion_ratio(
    foundation: FoundationState,
    reg_flags: Dict[str, bool],
    lifecycle: LifecycleState,
) -> float:
    f_parts = [
        foundation.jurisdiction_resolved,
        foundation.mobile_collected,
        foundation.mobile_verified,
        foundation.session_initialized,
    ]
    f_score = sum(1 for x in f_parts if x) / 4.0
    if foundation.passcode_created is True:
        f_score = min(1.0, f_score + 0.05)

    reg_keys = [
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
        # identity_foundation / financial_profile : agrégats (flags) — pas le ratio pour éviter double comptage
    ]
    r_score = sum(1 for k in reg_keys if reg_flags.get(k)) / float(len(reg_keys))

    if lifecycle.active_client:
        l_score = 1.0
    elif lifecycle.pe_client_linked:
        l_score = 0.75
    elif lifecycle.kyc_completed:
        l_score = 0.55
    elif lifecycle.kyc_pending:
        l_score = 0.25
    else:
        l_score = 0.0

    return round(0.2 * f_score + 0.5 * r_score + 0.3 * l_score, 3)


def _build_lists(
    foundation: FoundationState,
    reg_flags: Dict[str, bool],
    lifecycle: LifecycleState,
) -> Tuple[List[str], List[str]]:
    done: List[str] = []
    miss: List[str] = []

    def add(prefix: str, name: str, ok: bool) -> None:
        key = f"{prefix}:{name}"
        if ok:
            done.append(key)
        else:
            miss.append(key)

    add("foundation", "jurisdiction_resolved", foundation.jurisdiction_resolved)
    add("foundation", "mobile_collected", foundation.mobile_collected)
    add("foundation", "mobile_verified", foundation.mobile_verified)
    add("foundation", "session_initialized", foundation.session_initialized)
    if foundation.passcode_created is True:
        done.append("foundation:passcode_server_ack")
    elif foundation.passcode_created is False:
        miss.append("foundation:passcode_server_ack")

    for k, ok in reg_flags.items():
        add("registration", k, ok)

    add("lifecycle", "kyc_completed", lifecycle.kyc_completed)
    if lifecycle.kyc_pending:
        done.append("lifecycle:kyc_pending")
    add("lifecycle", "pe_client_linked", lifecycle.pe_client_linked)
    add("lifecycle", "active_client", lifecycle.active_client)

    return sorted(set(done)), sorted(set(miss))


def _session_snapshot(
    session: Optional[RegistrationSession],
    *,
    has_older_completed_session: bool,
) -> Optional[RegistrationSessionSnapshot]:
    if session is None:
        return None
    return RegistrationSessionSnapshot(
        session_id=session.id,
        status=session.status,
        flow_id=session.flow_id,
        flow_version=session.flow_version,
        current_step_key=session.current_step.step_key if session.current_step else None,
        current_screen_key=session.current_screen.screen_key if session.current_screen else None,
        progress_percent=session.progress_percent,
        updated_at=session.updated_at,
        has_older_completed_session=has_older_completed_session,
    )


@dataclass(frozen=True)
class RegistrationProgressSummary:
    """Ancienne forme — conservée pour compatibilité interne."""

    stage: RegistrationProgressStage
    label: str
    completion_ratio: float
    completed_steps: list[str]
    missing_steps: list[str]
    source_notes: str


def compute_canonical_registration_progress(
    db: Session,
    person: Person,
    pe_client: Optional[PeClient],
) -> RegistrationProgressBlock:
    session = _latest_registration_session(db, person.id)
    mobile_verified = _has_verified_sms_challenge(db, person.id)
    passcode_sig = _passcode_server_signal(person)

    foundation = FoundationState(
        jurisdiction_resolved=_jurisdiction_resolved(person),
        mobile_collected=_person_has_phone(person),
        mobile_verified=mobile_verified,
        passcode_created=passcode_sig,
        session_initialized=session is not None,
    )

    reg_flags, reg_completed = _registration_flags_with_source_priority(db, person, session)
    lifecycle = _lifecycle_flags(person, pe_client, registration_completed=reg_completed)

    macro = _macro_from_signals(
        person=person,
        foundation=foundation,
        reg_completed=reg_completed,
        lifecycle=lifecycle,
        session=session,
    )

    ratio = _completion_ratio(foundation, reg_flags, lifecycle)
    done, miss = _build_lists(foundation, reg_flags, lifecycle)
    has_older = bool(
        reg_completed
        and session is not None
        and (session.status or "").lower() != "completed"
    )
    snap = _session_snapshot(session, has_older_completed_session=has_older)

    notes = (
        f"person.kyc_status={person.kyc_status!r}; "
        f"latest_reg_session_status={session.status if session else None}; "
        f"any_reg_session_completed={reg_completed}; "
        f"has_older_completed_vs_latest_runtime={has_older}; "
        f"pe_client_id={pe_client.id if pe_client else None}; "
        f"pe_client.status={pe_client.status if pe_client else None}; "
        f"sot=multi_session_completed_any_plus_latest_runtime_union_profile"
    )

    return RegistrationProgressBlock(
        stage=macro,
        label=_macro_label(macro, foundation),
        completion_ratio=ratio,
        completed_steps=done,
        missing_steps=miss,
        source_notes=notes,
        foundation=foundation,
        registration=RegistrationStateFlags(
            identity_completed=reg_flags["identity"],
            dob_completed=reg_flags["date_of_birth"],
            residence_completed=reg_flags["residence_country"],
            address_completed=reg_flags["home_address"],
            email_completed=reg_flags["contact_email"],
            email_verification_optional=reg_flags["email_verification_optional"],
            terms_completed=reg_flags["terms"],
            registration_completed=reg_completed,
            employment_status_completed=reg_flags["employment_status"],
            work_sector_completed=reg_flags["work_sector"],
            work_details_completed=reg_flags["work_details"],
            annual_income_completed=reg_flags["annual_income"],
            net_worth_completed=reg_flags["net_worth"],
            source_of_wealth_completed=reg_flags["source_of_wealth"],
            financial_acknowledgements_completed=reg_flags["financial_acknowledgements"],
            identity_foundation_completed=reg_flags["identity_foundation"],
            financial_profile_completed=reg_flags["financial_profile"],
        ),
        lifecycle=lifecycle,
        session_snapshot=snap,
        legacy_stage=_legacy_stage(macro),
    )


def compute_registration_progress(
    db: Session,
    person: Person,
    pe_client: Optional[PeClient],
) -> RegistrationProgressSummary:
    """Ancienne API — préférer compute_canonical_registration_progress."""
    block = compute_canonical_registration_progress(db, person, pe_client)
    return RegistrationProgressSummary(
        stage=block.legacy_stage,
        label=block.label,
        completion_ratio=block.completion_ratio,
        completed_steps=block.completed_steps,
        missing_steps=block.missing_steps,
        source_notes=block.source_notes,
    )
