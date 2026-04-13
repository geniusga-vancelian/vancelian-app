"""Service Customer 360 — requêtes et agrégation.

Projection identité : la **source de vérité affichée** pour le customer est
``Person.profile_json[\"collected\"]`` (slugs métier). Les champs d’auth sur
``admin_users`` (ex. ``mobile_e164``) ne sont utilisés qu’en **repli** lorsque le
profil collecté est encore vide — jamais comme source primaire pour l’e-mail métier
(``admin_users.email`` est optionnel et ne remplace pas ``collected.email``).
Voir ``_extract_identity_fields`` pour le détail par champ.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, asc, cast, desc, func, or_, String
from sqlalchemy.orm import Session

from database import AdminUser, Person, RegistrationSession, TwoFactorChallenge
from services.portfolio_engine.clients.models import Client as PeClient
from services.registration.service import get_person_collected_value

from .registration_progress import compute_canonical_registration_progress
from services.custody.repository import CustodyAccountRepository

from .schemas import (
    CustomerAdminDetail,
    CustomerAdminListItem,
    CustomerAdminListResponse,
    CustomerCustodySearchItem,
    CustomerCustodySearchResponse,
    DebugSummary,
    IdentitySection,
    KycSection,
    RegistrationProgressBlock,
    RegistrationSection,
    RegistrationSessionSummary,
    SecurityPlaceholder,
    TransactionPlaceholder,
    WalletSummary,
)


def _eligible_person_filter(db: Session):
    """Personnes « customer » visibles au Customer 360.

    Inclut : parcours d’inscription, 2FA SMS historique, téléphone collecté sur le profil,
    **ou** compte app avec ``admin_users.mobile_e164`` (connexion mobile OTP sans encore de slug collecté).
    """
    reg_sub = (
        db.query(RegistrationSession.person_id)
        .filter(RegistrationSession.person_id.isnot(None))
        .distinct()
    )
    sms_sub = (
        db.query(TwoFactorChallenge.person_id)
        .filter(TwoFactorChallenge.channel.ilike("%sms%"))
        .distinct()
    )
    # Compte créé via app mobile : mobile sur la ligne d’auth même si profile_json pas encore aligné.
    app_mobile_sub = (
        db.query(AdminUser.person_id)
        .filter(
            AdminUser.person_id.isnot(None),
            AdminUser.mobile_e164.isnot(None),
            func.trim(AdminUser.mobile_e164) != "",
        )
        .distinct()
    )
    c = Person.profile_json["collected"]
    phone_slugs = ("phone_e164", "national_phone_number", "phone", "mobile_e164", "mobile_phone")
    collected_phone = or_(
        *[
            and_(c[k].astext.isnot(None), c[k].astext != "")
            for k in phone_slugs
        ]
    )
    return or_(
        Person.id.in_(reg_sub),
        Person.id.in_(sms_sub),
        Person.id.in_(app_mobile_sub),
        collected_phone,
    )


def _extract_identity_fields(person: Person, db: Session) -> dict[str, Any]:
    """Champs identité pour liste / fiche Customer 360.

    Référence rapide (auth vs customer) :

    - **mobile** — canon : ``collected`` (plusieurs slugs téléphone). Repli :
      ``admin_users.mobile_e164`` si vide (alignement progressif / backfill).
    - **email** — canon : ``collected.email`` uniquement. Pas de repli sur
      ``admin_users.email`` (placeholder signup / login technique).
    - **first_name / last_name** — canon : ``collected`` (aliases ``given_name`` /
      ``family_name``). Pas de projection depuis l’auth.
    - **country_of_residence** — canon : ``collected`` (aliases ``country``,
      ``residence_country``). Pas d’équivalent auth.
    - **jurisdiction** — hors de ce dict : ``Person.jurisdiction`` (colonne SQL).
    - **Statut « customer »** — identité : ``Person.status`` (``person_status``) ;
      produit portefeuille : ``pe_clients.status`` (``wallet.client_status``), distinct.

    Repli **liste** : ``list_customers`` peut afficher ``pe_clients.email`` si
    ``collected.email`` est vide (voir appelant).
    """
    mobile = (
        get_person_collected_value(person, "phone_e164")
        or get_person_collected_value(person, "national_phone_number")
        or get_person_collected_value(person, "phone")
        or get_person_collected_value(person, "mobile_e164")
    )
    if not (str(mobile or "").strip()):
        u = (
            db.query(AdminUser)
            .filter(AdminUser.person_id == person.id)
            .first()
        )
        if u is not None and getattr(u, "mobile_e164", None):
            mobile = str(u.mobile_e164).strip()

    return {
        "mobile": mobile,
        "email": get_person_collected_value(person, "email"),
        "first_name": get_person_collected_value(person, "first_name")
        or get_person_collected_value(person, "given_name"),
        "last_name": get_person_collected_value(person, "last_name")
        or get_person_collected_value(person, "family_name"),
        "country_of_residence": get_person_collected_value(person, "country_of_residence")
        or get_person_collected_value(person, "country")
        or get_person_collected_value(person, "residence_country"),
        "date_of_birth": get_person_collected_value(person, "date_of_birth")
        or get_person_collected_value(person, "birth_date"),
        "nationality": get_person_collected_value(person, "nationality"),
    }


def _displayable_collected_email(person: Person) -> Optional[str]:
    """E-mail optionnel pour l'UI : uniquement depuis le profil collecté — jamais ``pe_clients.email``."""
    raw = get_person_collected_value(person, "email")
    if not raw or not str(raw).strip():
        return None
    e = str(raw).strip()
    el = e.lower()
    if "@" not in el:
        return None
    return e[:320]


def pe_client_for_person_or_raise(db: Session, person_id: UUID) -> PeClient:
    """Client PE lié à la personne — requis pour proxies documents (PDF)."""
    person = db.query(Person).filter(Person.id == person_id).first()
    if person is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    pe = _pe_client_for_person(db, person)
    if pe is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun compte portefeuille (PE) rattaché à cette personne — documents indisponibles.",
        )
    return pe


def _pe_client_for_person(db: Session, person: Person) -> Optional[PeClient]:
    return (
        db.query(PeClient)
        .filter(PeClient.person_id == person.id)
        .one_or_none()
    )


def _to_progress_block(person: Person, pe: Optional[PeClient], db: Session) -> RegistrationProgressBlock:
    return compute_canonical_registration_progress(db, person, pe)


def list_customers(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    q: Optional[str] = None,
    sort: str = "-updated_at",
    country: Optional[str] = None,
) -> CustomerAdminListResponse:
    """Liste paginée des personnes éligibles."""
    q = (q or "").strip()
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    base = db.query(Person).filter(_eligible_person_filter(db))

    if country:
        cc = country.strip().upper()
        c = Person.profile_json["collected"]
        base = base.filter(
            or_(
                func.upper(c["country_of_residence"].astext) == cc,
                func.upper(c["country"].astext) == cc,
                func.upper(c["residence_country"].astext) == cc,
            )
        )

    if q:
        like = f"%{q}%"
        c = Person.profile_json["collected"]
        base = base.filter(
            or_(
                cast(Person.profile_json, String).ilike(like),
                c["email"].astext.ilike(like),
                c["phone_e164"].astext.ilike(like),
                c["first_name"].astext.ilike(like),
                c["last_name"].astext.ilike(like),
            )
        )

    total = base.count()

    order_col = Person.updated_at
    sort_field = sort.lstrip("-")
    if sort_field == "created_at":
        order_col = Person.created_at
    elif sort_field == "updated_at":
        order_col = Person.updated_at
    is_desc = sort.startswith("-")
    base = base.order_by(desc(order_col) if is_desc else asc(order_col))

    rows = base.offset((page - 1) * page_size).limit(page_size).all()

    items: list[CustomerAdminListItem] = []
    for person in rows:
        pe = _pe_client_for_person(db, person)
        fields = _extract_identity_fields(person, db)
        email = fields.get("email") or (pe.email if pe else None)
        items.append(
            CustomerAdminListItem(
                person_id=person.id,
                mobile=fields.get("mobile"),
                email=email,
                first_name=fields.get("first_name"),
                last_name=fields.get("last_name"),
                country_of_residence=fields.get("country_of_residence"),
                registration_progress=_to_progress_block(person, pe, db),
                created_at=person.created_at,
                updated_at=person.updated_at,
                pe_client_id=pe.id if pe else None,
            )
        )

    return CustomerAdminListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


def search_customers_for_custody(
    db: Session,
    *,
    q: str,
    limit: int = 20,
) -> CustomerCustodySearchResponse:
    """Recherche pour sélection custody : identité ``person_id`` + ``phone_e164`` ; e-mail optionnel (collecté filtré)."""
    raw = (q or "").strip()
    if len(raw) < 2:
        return CustomerCustodySearchResponse(items=[], total=0)

    limit = min(max(1, limit), 50)
    base = db.query(Person).filter(_eligible_person_filter(db))

    like = f"%{raw}%"
    c = Person.profile_json["collected"]
    text_cond = or_(
        cast(Person.profile_json, String).ilike(like),
        c["email"].astext.ilike(like),
        c["phone_e164"].astext.ilike(like),
        c["first_name"].astext.ilike(like),
        c["last_name"].astext.ilike(like),
    )

    try:
        quid = UUID(raw)
        uuid_cond = Person.id == quid
        base = base.filter(or_(uuid_cond, text_cond))
    except ValueError:
        base = base.filter(text_cond)

    rows = base.order_by(desc(Person.updated_at)).limit(limit).all()

    acc_repo = CustodyAccountRepository()
    items: list[CustomerCustodySearchItem] = []
    for person in rows:
        pe = _pe_client_for_person(db, person)
        fields = _extract_identity_fields(person, db)
        fn = (fields.get("first_name") or "").strip()
        ln = (fields.get("last_name") or "").strip()
        display_name = f"{fn} {ln}".strip() or None
        phone = (fields.get("mobile") or "").strip() or None
        opt_email = _displayable_collected_email(person)
        has_euro = False
        if pe is not None:
            existing = acc_repo.find_client_account(db, pe.id, "EUR")
            has_euro = existing is not None
        items.append(
            CustomerCustodySearchItem(
                person_id=person.id,
                phone_e164=phone,
                optional_email=opt_email,
                display_name=display_name,
                has_euro_account=has_euro,
                pe_client_id=pe.id if pe else None,
            )
        )

    return CustomerCustodySearchResponse(items=items, total=len(items))


def get_customer_detail(db: Session, person_id: UUID) -> Optional[CustomerAdminDetail]:
    person = db.query(Person).filter(Person.id == person_id).first()
    if person is None:
        return None
    if not db.query(Person).filter(Person.id == person_id).filter(_eligible_person_filter(db)).first():
        return None

    pe = _pe_client_for_person(db, person)
    fields = _extract_identity_fields(person, db)
    email = fields.get("email") or (pe.email if pe else None)

    reg_block = compute_canonical_registration_progress(db, person, pe)
    snap = reg_block.session_snapshot
    reg_sec = RegistrationSection(
        latest_session=(
            RegistrationSessionSummary(
                session_id=snap.session_id,
                status=snap.status,
                progress_percent=snap.progress_percent,
                flow_id=snap.flow_id,
                flow_version=snap.flow_version,
                current_step_key=snap.current_step_key,
                current_screen_key=snap.current_screen_key,
                updated_at=snap.updated_at,
            )
            if snap
            else None
        ),
        availability="available" if snap else "placeholder",
    )

    pj = person.profile_json or {}
    collected = pj.get("collected") if isinstance(pj.get("collected"), dict) else {}
    slugs = sorted(collected.keys())[:40]

    identity = IdentitySection(
        person_id=person.id,
        pe_client_id=pe.id if pe else None,
        login_frozen=bool(getattr(person, "login_frozen", False)),
        mobile=fields.get("mobile"),
        email=email,
        first_name=fields.get("first_name"),
        last_name=fields.get("last_name"),
        date_of_birth=fields.get("date_of_birth"),
        nationality=fields.get("nationality"),
        country_of_residence=fields.get("country_of_residence"),
        jurisdiction=person.jurisdiction,
        person_status=person.status,
        person_created_at=person.created_at,
        person_updated_at=person.updated_at,
        availability="rich" if len(slugs) > 3 else "partial",
    )

    wallet = WalletSummary(
        pe_client_id=pe.id if pe else None,
        email=pe.email if pe else None,
        client_status=pe.status if pe else None,
        kyc_status=pe.kyc_status if pe else None,
        reference_currency=pe.reference_currency if pe else None,
        availability="available" if pe else "not_available",
    )

    excerpt = {k: collected[k] for k in list(collected.keys())[:25]}

    return CustomerAdminDetail(
        identity=identity,
        registration=reg_sec,
        registration_progress=reg_block,
        kyc=KycSection(
            kyc_status=person.kyc_status,
            notes="person.kyc_status ; enrichissement AML / documents : à brancher.",
            availability="partial",
        ),
        wallet=wallet,
        transactions=TransactionPlaceholder(),
        security=SecurityPlaceholder(),
        debug=DebugSummary(
            person_profile_keys=sorted(pj.keys()) if isinstance(pj, dict) else [],
            collected_slugs_sample=slugs,
            hints="Aperçu contrôlé — pas de dump complet du profil.",
        ),
        raw_profile_excerpt=excerpt if excerpt else None,
    )
