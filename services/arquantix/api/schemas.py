"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime
import uuid


# Auth
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    device_id: Optional[str] = Field(
        default=None,
        description="Identifiant d’appareil lié à la session (PR B) — renvoyé après login lorsque généré côté serveur.",
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RevokeTokenRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdaptiveAuthOrchestrateRequest(BaseModel):
    """Pré-décision login (même anti-énumération que les starts : utilisateur inconnu → réponse générique)."""

    identifier: str = Field(..., min_length=3, max_length=255)
    identifier_type: Literal["phone_e164", "email"]


class AdaptiveAuthDecisionPayload(BaseModel):
    """Décision sérialisable (orchestrateur adaptatif)."""

    primary_method: str
    fallback_methods: List[str] = Field(default_factory=list)
    auto_trigger_passkey: bool = False
    step_up_required: bool = False
    local_biometric_recommended: bool = False
    blocked: bool = False
    reason_codes: List[str] = Field(default_factory=list)
    device_trust_level: str = "LOW"
    login_risk_score: int = 0
    fraud_score: Optional[float] = None
    auth_strength_target: str = "otp"
    session_trust_target: str = "UNKNOWN"
    ui_variant: str = "standard"


class SessionIntelligenceResponse(BaseModel):
    """Lecture admin — état Session Intelligence pour une session auth."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    user_id: int
    auth_strength: str
    session_trust_level: str
    device_trust_level: str
    last_risk_score: int
    last_fraud_score: Optional[float] = None
    last_activity_at: datetime
    last_sensitive_action_at: Optional[datetime] = None
    last_ip: Optional[str] = None
    last_country: Optional[str] = None
    relock_required: bool
    step_up_required: bool
    last_step_up_at: Optional[datetime] = None
    reason_codes_json: List[Any] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# Passkeys / WebAuthn (Phase 3.2)
class PasskeyRegisterStartBody(BaseModel):
    device_label: Optional[str] = None


class PasskeyRegisterStartResponse(BaseModel):
    options: Dict[str, Any]
    challenge_token: str


class PasskeyRegisterFinishRequest(BaseModel):
    challenge_token: str
    credential: Dict[str, Any]
    device_label: Optional[str] = None


class PasskeyRegisterFinishResponse(BaseModel):
    credential_id: str
    status: str = "ok"


class PasskeyLoginStartRequest(BaseModel):
    email: EmailStr


class PasskeyLoginStartResponse(BaseModel):
    options: Dict[str, Any]
    challenge_token: str


class PasskeyLoginFinishRequest(BaseModel):
    challenge_token: str
    credential: Dict[str, Any]


class PasskeyPublicItem(BaseModel):
    id: uuid.UUID
    credential_id: str
    device_label: Optional[str] = None
    transports: Optional[Any] = None
    aaguid: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None


class PasskeyRevokeRequest(BaseModel):
    credential_id: str


class PasskeyPromptRequest(BaseModel):
    """Télémétrie prompt passkey (Phase 3.3) — ne remplace pas l’audit login/register."""

    event: str
    identifier_domain: Optional[str] = None
    detail: Optional[str] = Field(None, max_length=200)


class PasskeysSecurityConfigResponse(BaseModel):
    """Diagnostic WebAuthn / passkeys (admin) — Phase 3.4."""

    rp_id: str
    rp_name: str
    origins: List[str]
    passkeys_enabled: bool
    admin_email_otp_enabled: bool
    environment: str
    strict_webauthn_validation: bool
    associated_domains_expected: List[str]
    webcredentials_apps_template: List[str]
    assetlinks_expected: Optional[Any] = None
    warnings: List[str]
    well_known_probe: Optional[Dict[str, Any]] = None


class AuthSessionItem(BaseModel):
    """Session refresh active (liste « mes appareils »)."""

    id: uuid.UUID
    device_id: str
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_trust_level: Optional[str] = None
    step_up_otp_required: Optional[bool] = None

    class Config:
        from_attributes = True


class AuthSecurityEventItem(BaseModel):
    """Événement de sécurité (admin read-only)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: Optional[int] = None
    device_id: str
    event_type: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_payload")


class AuthSecurityEventsSummary(BaseModel):
    """Résumé + drapeaux de corrélation (pas de blocage automatique)."""

    total_window: int
    counts_by_type: Dict[str, int]
    anomaly_flags: Dict[str, Any]


class SecurityCorrelationFindingSchema(BaseModel):
    """Finding corrélation SIEM (admin)."""

    rule: str
    severity: str
    detail: Dict[str, Any]


class SecurityAnomaliesResponse(BaseModel):
    """Résultat moteur de corrélation + drapeaux historiques Phase 3.1."""

    generated_at: datetime
    findings: List[SecurityCorrelationFindingSchema]
    legacy_flags: Dict[str, Any]
    global_risk_index: int = Field(default=0, ge=0, le=100)
    global_risk_level: str = "LOW"
    engine_signals: List[Dict[str, Any]] = Field(default_factory=list)


class SecurityUserRiskResponse(BaseModel):
    """Profil risque synthétique pour un utilisateur admin."""

    user_id: int
    risk_score: str
    risk_index: int = Field(default=0, ge=0, le=100)
    findings: List[SecurityCorrelationFindingSchema]
    recent_event_count: int
    engine_signals: List[Dict[str, Any]] = Field(default_factory=list)


class AdminSecurityUserIdBody(BaseModel):
    user_id: int = Field(..., ge=1)


class AdminSecurityActionResponse(BaseModel):
    ok: bool = True
    detail: str = ""


class FraudMLModelInfoResponse(BaseModel):
    loaded: bool
    model_version: Optional[str] = None
    model_kind: Optional[str] = None
    trained_at_utc: Optional[str] = None
    feature_keys: List[str] = Field(default_factory=list)
    storage_path: Optional[str] = None


class FraudMLPredictResponse(BaseModel):
    user_id: int
    heuristic_score: int
    hybrid_score: int
    enforcement_score: int
    risk_level: str
    ml_available: bool
    ml_score: Optional[float] = None
    ml_confidence: Optional[float] = None
    model_version: Optional[str] = None
    ml_weight: float = 0.4
    ml_enforce_gate: int = 45
    feature_vector: Dict[str, float] = Field(default_factory=dict)


class DeviceReputationItem(BaseModel):
    device_hash: str
    global_risk_score: int
    reputation_level: str
    total_sessions: int
    unique_user_count: int
    unique_ip_count: int
    suspicious_event_count: int
    blocked_until: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeviceGraphFindingItem(BaseModel):
    id: uuid.UUID
    device_hash: Optional[str] = None
    user_id: Optional[int] = None
    finding_type: str
    severity: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceBlacklistRequest(BaseModel):
    device_hash: str = Field(..., min_length=16, max_length=64)
    reason: str = Field(..., min_length=1, max_length=512)
    blocked_until: Optional[datetime] = None


class DeviceUnblacklistRequest(BaseModel):
    device_hash: str = Field(..., min_length=16, max_length=64)


class DeviceReputationActionResponse(BaseModel):
    ok: bool = True
    detail: str = ""


# Global Settings
class GlobalSettingsResponse(BaseModel):
    id: int
    site_name: str
    tagline: Optional[str]
    socials_json: Dict[str, Any]
    seo_json: Dict[str, Any]
    updated_at: datetime

    class Config:
        from_attributes = True


class GlobalSettingsUpdate(BaseModel):
    site_name: Optional[str] = None
    tagline: Optional[str] = None
    socials_json: Optional[Dict[str, Any]] = None
    seo_json: Optional[Dict[str, Any]] = None


# Pages
class PageBase(BaseModel):
    slug: str
    locale: str = "fr"
    title: str
    sections_json: Optional[Dict[str, Any]] = {}
    seo_json: Optional[Dict[str, Any]] = {}


class PageCreate(PageBase):
    pass


class PageUpdate(BaseModel):
    slug: Optional[str] = None
    locale: Optional[str] = None
    title: Optional[str] = None
    sections_json: Optional[Dict[str, Any]] = None
    seo_json: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    translation_status: Optional[str] = None


class PageResponse(PageBase):
    id: int
    status: str
    published_at: Optional[datetime]
    updated_at: datetime
    source_page_id: Optional[int] = None
    translation_status: str = "manual"
    translation_meta_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# News
class NewsBase(BaseModel):
    slug: str
    locale: str = "fr"
    title: str
    excerpt: Optional[str] = None
    content_markdown: Optional[str] = None
    cover_image_url: Optional[str] = None


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    slug: Optional[str] = None
    locale: Optional[str] = None
    title: Optional[str] = None
    excerpt: Optional[str] = None
    content_markdown: Optional[str] = None
    cover_image_url: Optional[str] = None
    status: Optional[str] = None


class NewsResponse(NewsBase):
    id: int
    status: str
    published_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


# Contact Submissions
class ContactSubmissionCreate(BaseModel):
    name: str
    email: EmailStr
    message: str


class ContactSubmissionResponse(BaseModel):
    id: int
    name: str
    email: str
    message: str
    ip: Optional[str]
    user_agent: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Persons
class PersonResponse(BaseModel):
    id: uuid.UUID
    status: str
    jurisdiction: Optional[str]
    profile_json: Dict[str, Any]
    client_id: Optional[uuid.UUID] = None
    kyc_status: str = "not_started"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SetFieldRequest(BaseModel):
    slug: Optional[str] = None
    field_definition_id: Optional[uuid.UUID] = None
    value: Any
    correlation_id: Optional[uuid.UUID] = None

