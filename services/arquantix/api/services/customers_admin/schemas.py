"""Schémas Pydantic — Customer 360 admin."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RegistrationMacroStage(str, Enum):
    """Stade macro unique (priorité déterministe côté registration_progress)."""

    PHONE_STARTED = "phone_started"
    ACCOUNT_SECURED = "account_secured"
    REGISTRATION_IN_PROGRESS = "registration_in_progress"
    KYC_PENDING = "kyc_pending"
    KYC_COMPLETED = "kyc_completed"
    PE_CLIENT_LINKED = "pe_client_linked"
    ACTIVE_CLIENT = "active_client"


class RegistrationProgressStage(str, Enum):
    """Ancien regroupement — legacy_stage."""

    PHONE_STARTED = "phone_started"
    PROFILE_PARTIAL = "profile_partial"
    REGISTRATION_ACTIVE = "registration_active"
    REGISTRATION_COMPLETED = "registration_completed"
    KYC_PENDING = "kyc_pending"
    KYC_APPROVED = "kyc_approved"
    PE_CLIENT_LINKED = "pe_client_linked"
    ACTIVE_CLIENT = "active_client"


class FoundationState(BaseModel):
    """Fondation compte (hors champs du flow registration engine)."""

    jurisdiction_resolved: bool = False
    mobile_collected: bool = False
    mobile_verified: bool = False
    passcode_created: Optional[bool] = Field(
        default=None,
        description=(
            "True si ack serveur explicite (ex. security.local_passcode_registered_at). "
            "None si inconnu — le passcode peut être uniquement local (secure storage)."
        ),
    )
    session_initialized: bool = False


class RegistrationStateFlags(BaseModel):
    """Aligné sur les étapes canoniques du flow EU (extensible — v3 financial_profile)."""

    identity_completed: bool = False
    dob_completed: bool = False
    residence_completed: bool = False
    address_completed: bool = False
    email_completed: bool = False
    email_verification_optional: bool = False
    terms_completed: bool = False
    registration_completed: bool = False
    employment_status_completed: bool = False
    work_sector_completed: bool = False
    work_details_completed: bool = False
    annual_income_completed: bool = False
    net_worth_completed: bool = False
    source_of_wealth_completed: bool = False
    financial_acknowledgements_completed: bool = False
    identity_foundation_completed: bool = False
    financial_profile_completed: bool = False


class LifecycleState(BaseModel):
    kyc_pending: bool = False
    kyc_completed: bool = False
    pe_client_linked: bool = False
    active_client: bool = False


class RegistrationSessionSnapshot(BaseModel):
    session_id: Optional[UUID] = None
    status: Optional[str] = None
    flow_id: Optional[UUID] = None
    flow_version: Optional[int] = None
    current_step_key: Optional[str] = None
    current_screen_key: Optional[str] = None
    progress_percent: Optional[int] = None
    updated_at: Optional[datetime] = None
    has_older_completed_session: bool = Field(
        default=False,
        description=(
            "True si une session antérieure est en status completed alors que le snapshot "
            "ci-dessus est la session la plus récente (runtime) non completed."
        ),
    )


class RegistrationProgressBlock(BaseModel):
    """Progression canonique — le frontend n’a pas à recalculer."""

    stage: RegistrationMacroStage
    label: str
    completion_ratio: float = Field(ge=0.0, le=1.0)
    completed_steps: List[str] = []
    missing_steps: List[str] = []
    source_notes: str = ""
    foundation: FoundationState = Field(default_factory=FoundationState)
    registration: RegistrationStateFlags = Field(default_factory=RegistrationStateFlags)
    lifecycle: LifecycleState = Field(default_factory=LifecycleState)
    session_snapshot: Optional[RegistrationSessionSnapshot] = None
    legacy_stage: RegistrationProgressStage = Field(
        description="Ancien regroupement pour compat outils / comparaisons.",
    )


class CustomerAdminListItem(BaseModel):
    person_id: UUID
    mobile: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    country_of_residence: Optional[str] = None
    registration_progress: RegistrationProgressBlock
    created_at: datetime
    updated_at: datetime
    pe_client_id: Optional[UUID] = None


class CustomerAdminListResponse(BaseModel):
    items: List[CustomerAdminListItem]
    total: int
    page: int
    page_size: int


class CustomerCustodySearchItem(BaseModel):
    """Sélection custody : identifiants ``person_id`` + ``phone_e164`` ; e-mail optionnel (profil collecté filtré uniquement)."""

    person_id: UUID
    phone_e164: Optional[str] = None
    optional_email: Optional[str] = Field(
        default=None,
        description="E-mail depuis le profil collecté uniquement ; absent si placeholder / interne.",
    )
    display_name: Optional[str] = None
    has_euro_account: bool = False
    pe_client_id: Optional[UUID] = None


class CustomerCustodySearchResponse(BaseModel):
    items: List[CustomerCustodySearchItem]
    total: int


class IdentitySection(BaseModel):
    person_id: UUID
    pe_client_id: Optional[UUID] = None
    login_frozen: bool = False
    mobile: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    country_of_residence: Optional[str] = None
    jurisdiction: Optional[str] = None
    person_status: str
    person_created_at: datetime
    person_updated_at: datetime
    availability: Literal["partial", "rich"] = "partial"


class RegistrationSessionSummary(BaseModel):
    session_id: Optional[UUID] = None
    status: Optional[str] = None
    progress_percent: Optional[int] = None
    flow_id: Optional[UUID] = None
    flow_version: Optional[int] = None
    current_step_key: Optional[str] = None
    current_screen_key: Optional[str] = None
    updated_at: Optional[datetime] = None


class RegistrationSection(BaseModel):
    latest_session: Optional[RegistrationSessionSummary] = None
    availability: Literal["available", "placeholder"] = "available"


class KycSection(BaseModel):
    kyc_status: str
    notes: Optional[str] = None
    availability: Literal["partial", "placeholder"] = "partial"


class WalletSummary(BaseModel):
    pe_client_id: Optional[UUID] = None
    email: Optional[str] = None
    client_status: Optional[str] = None
    kyc_status: Optional[str] = None
    reference_currency: Optional[str] = None
    availability: Literal["available", "not_available"] = "not_available"


class TransactionPlaceholder(BaseModel):
    message: str = "Not available yet — agrégation transactions à brancher."
    availability: Literal["placeholder"] = "placeholder"


class SecurityPlaceholder(BaseModel):
    message: str = "Résumé sessions / événements sécurité : extension prévue."
    availability: Literal["placeholder"] = "placeholder"


class DebugSummary(BaseModel):
    person_profile_keys: List[str] = Field(default_factory=list)
    collected_slugs_sample: List[str] = Field(default_factory=list)
    hints: str = ""


class CustomerAdminDetail(BaseModel):
    identity: IdentitySection
    registration: RegistrationSection
    registration_progress: RegistrationProgressBlock
    kyc: KycSection
    wallet: WalletSummary
    transactions: TransactionPlaceholder
    security: SecurityPlaceholder
    debug: DebugSummary
    raw_profile_excerpt: Optional[dict[str, Any]] = Field(
        default=None,
        description="Extrait léger profile_json.collected pour support (pas un dump complet).",
    )
