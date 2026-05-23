"""
Database configuration and models
"""
# CRITICAL: Load environment variables FIRST
from dotenv import load_dotenv
from pathlib import Path

# Force load .env.local first, then .env (explicit order)
api_dir = Path(__file__).parent
def _safe_load_dotenv(path: Path) -> None:
    try:
        load_dotenv(path)
    except PermissionError:
        # Skip unreadable env files (e.g. OneDrive/ACL issues)
        return

_safe_load_dotenv(api_dir / ".env.local")  # Priority: .env.local first
_safe_load_dotenv(api_dir / ".env")  # Then .env

from sqlalchemy import create_engine, Column, Integer, SmallInteger, String, Text, DateTime, JSON, Enum as SQLEnum, Date, Numeric, BigInteger, ForeignKey, Boolean, Index, UniqueConstraint, text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from datetime import date as date_type
import enum
import uuid
import os

# Database URL - Now properly loaded from .env.local
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('DB_USER', 'arquantix')}:{os.getenv('DB_PASSWORD', 'arquantix')}@{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', '5443')}/{os.getenv('DB_NAME', 'arquantix_fresh')}"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class StatusEnum(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class GlobalSettings(Base):
    __tablename__ = "global_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    site_name = Column(String(255), nullable=False, default="Arquantix")
    tagline = Column(String(500), nullable=True)
    socials_json = Column(JSON, nullable=True, default={})
    seo_json = Column(JSON, nullable=True, default={})
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Page(Base):
    """Legacy JSON-backed pages (FastAPI). Renamed from `pages` to avoid clash with Prisma `pages`."""

    __tablename__ = "legacy_json_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(255), nullable=False)
    locale = Column(String(10), nullable=False, default="fr")
    title = Column(String(500), nullable=False)
    sections_json = Column(JSON, nullable=True, default={})
    seo_json = Column(JSON, nullable=True, default={})
    status = Column(SQLEnum(StatusEnum), nullable=False, default=StatusEnum.DRAFT)
    published_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Translation fields
    source_page_id = Column(Integer, nullable=True)
    translation_status = Column(String(50), nullable=False, default="manual")
    translation_meta_json = Column(JSON, nullable=True)
    
    __table_args__ = (
        {"schema": "public"},
    )


class News(Base):
    __tablename__ = "news"
    
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(255), nullable=False)
    locale = Column(String(10), nullable=False, default="fr")
    title = Column(String(500), nullable=False)
    excerpt = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=True)
    cover_image_url = Column(String(1000), nullable=True)
    status = Column(SQLEnum(StatusEnum), nullable=False, default=StatusEnum.DRAFT)
    published_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        {"schema": "public"},
    )


class ContactSubmission(Base):
    __tablename__ = "contact_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    name_encrypted = Column(Text, nullable=True)
    email_encrypted = Column(Text, nullable=True)
    message_encrypted = Column(Text, nullable=True)
    ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AdminUser(Base):
    """Magasin technique des **identifiants de connexion applicatifs** (JWT, OTP SMS, passkeys).

    Le nom de table est historique (« admin ») : une ligne peut être un compte **staff**
    back-office *ou* un compte **client mobile / web** (e-mail, hash mot de passe,
    ``mobile_e164``, liaison ``person_id``). Ce n’est **pas** par nature un « compte
    administrateur produit » — utiliser ``zero_trust_role``, ``mobile_app_allowed`` et
    le contexte route pour distinguer opérateur vs client.
    """

    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    # Nullable (PR4) — identité JWT = id ; unique partiel en base (WHERE email IS NOT NULL).
    email = Column(String(255), nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    security_account_locked_until = Column(DateTime(timezone=True), nullable=True)
    security_flagged = Column(Boolean, nullable=False, server_default=text("false"))
    security_refresh_blocked = Column(Boolean, nullable=False, server_default=text("false"))
    zero_trust_role = Column(String(32), nullable=False, server_default=text("'admin'"))
    mobile_e164 = Column(String(24), nullable=True, unique=True, index=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("public.persons.id", ondelete="SET NULL"), nullable=True, unique=True)
    # False = compte back-office web uniquement (pas de session JWT / app Flutter).
    mobile_app_allowed = Column(Boolean, nullable=False, server_default=text("true"))


class AuthGlobalRiskScore(Base):
    """Score de risque global consolidé (SIEM + fraude + confiance appareil)."""

    __tablename__ = "auth_global_risk_score"
    __table_args__ = ({"schema": "public"},)

    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), primary_key=True)
    score = Column(Integer, nullable=False, server_default=text("0"))
    level = Column(String(32), nullable=False, server_default=text("'LOW'"))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AuthSession(Base):
    """Session serveur liée à un refresh token rotatif (Phase 2 auth hardening)."""

    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_user_id", "user_id"),
        Index("ix_auth_sessions_refresh_jti", "refresh_jti", unique=True),
        Index("ix_auth_sessions_user_device", "user_id", "device_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(128), nullable=False)
    refresh_jti = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoke_reason = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    fingerprint_hash = Column(String(64), nullable=True)
    fingerprint_metadata = Column(JSONB, nullable=True)
    attestation_type = Column(String(64), nullable=True)
    attestation_verified_at = Column(DateTime(timezone=True), nullable=True)
    attestation_metadata = Column(JSONB, nullable=True)
    # PR E — LOW | MEDIUM | HIGH (confiance attestation matérielle), distinct de device_trust_level
    device_attestation_tier = Column(String(16), nullable=True)
    device_trust_level = Column(String(32), nullable=False, server_default=text("'UNKNOWN'"))
    step_up_otp_required = Column(Boolean, nullable=False, server_default=text("false"))
    auth_strength = Column(String(64), nullable=False, server_default=text("'password'"))

    user = relationship("AdminUser", backref="auth_sessions")


class AuthRefreshToken(Base):
    """Historique des JTIs refresh par session — rotation, détection de reuse post-rotation."""

    __tablename__ = "auth_refresh_tokens"
    __table_args__ = (
        Index("ix_auth_refresh_tokens_session_id", "session_id"),
        Index("ix_auth_refresh_tokens_jti", "jti", unique=True),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.auth_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    jti = Column(String(64), nullable=False)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by_jti = Column(String(64), nullable=True)

    session = relationship("AuthSession", backref=backref("refresh_token_rows", lazy="dynamic"))


class AuthSessionIntelligence(Base):
    """État de sécurité continu par session (Session Intelligence + continuous auth)."""

    __tablename__ = "auth_session_intelligence"
    __table_args__ = (
        Index("ix_auth_session_intelligence_user_id", "user_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.auth_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    auth_strength = Column(String(64), nullable=False, server_default=text("'password'"))
    session_trust_level = Column(String(32), nullable=False, server_default=text("'UNKNOWN'"))
    device_trust_level = Column(String(32), nullable=False, server_default=text("'UNKNOWN'"))
    last_risk_score = Column(Integer, nullable=False, server_default=text("0"))
    last_fraud_score = Column(Float, nullable=True)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_sensitive_action_at = Column(DateTime(timezone=True), nullable=True)
    last_ip = Column(String(45), nullable=True)
    last_country = Column(String(8), nullable=True)
    relock_required = Column(Boolean, nullable=False, server_default=text("false"))
    step_up_required = Column(Boolean, nullable=False, server_default=text("false"))
    last_step_up_at = Column(DateTime(timezone=True), nullable=True)
    reason_codes_json = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    session = relationship("AuthSession", backref=backref("intelligence", uselist=False))
    user = relationship("AdminUser", backref="session_intelligence_rows")


class AuthDeviceCredential(Base):
    """PR D2 — clé publique ECDSA P-256 par (utilisateur, device_id logique) pour ``X-Device-Signature``."""

    __tablename__ = "auth_device_credentials"
    __table_args__ = (
        Index("ix_auth_device_credentials_user_id", "user_id"),
        UniqueConstraint("user_id", "device_id", name="uq_auth_device_credentials_user_device"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(128), nullable=False)
    public_key_spki_b64 = Column(Text, nullable=False)
    key_alg = Column(String(32), nullable=False, server_default=text("'EC_P256'"))
    attestation_level = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    device_label = Column(String(128), nullable=True)
    public_key_sha256_hex = Column(String(64), nullable=True)
    attestation_bound_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("AdminUser", backref="auth_device_credentials")


class AuthDeviceSignatureNonce(Base):
    """PR D3 — nonce usage unique pour signatures sensibles (anti-replay)."""

    __tablename__ = "auth_device_signature_nonces"
    __table_args__ = (
        Index("ix_auth_device_signature_nonces_user_device", "user_id", "device_id"),
        Index("ix_auth_device_signature_nonces_expires", "expires_at"),
        UniqueConstraint("nonce_hash", name="uq_auth_device_signature_nonces_hash"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(128), nullable=False)
    nonce_hash = Column(String(64), nullable=False)
    purpose = Column(String(32), nullable=False)
    # PR D4 — nullable = comportement PR D3 (nonce global « sensitive »)
    route_path = Column(String(512), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("AdminUser", backref="auth_device_signature_nonces")


class AuthUserDeviceProfile(Base):
    """Profil device par utilisateur : confiance login, compteurs, dernière empreinte / IP."""

    __tablename__ = "auth_user_device_profiles"
    __table_args__ = (
        Index("ix_auth_user_device_profiles_user_id", "user_id"),
        Index("ix_auth_user_device_profiles_device_hash", "device_hash"),
        UniqueConstraint("user_id", "device_hash", name="uq_auth_user_device_profiles_user_device"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    device_hash = Column(String(64), nullable=False)
    device_id = Column(String(128), nullable=True)
    fingerprint_hash = Column(String(64), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    login_count = Column(Integer, nullable=False, server_default=text("0"))
    successful_login_count = Column(Integer, nullable=False, server_default=text("0"))
    failed_login_count = Column(Integer, nullable=False, server_default=text("0"))
    last_ip = Column(String(45), nullable=True)
    last_country = Column(String(8), nullable=True)
    trust_score = Column(Integer, nullable=False, server_default=text("0"))
    trust_level = Column(String(16), nullable=False, server_default=text("'LOW'"))
    is_primary = Column(Boolean, nullable=True)
    last_auth_strength = Column(String(64), nullable=True)
    last_attestation_level = Column(String(64), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("AdminUser", backref="auth_user_device_profiles")


class AuthUserRiskBaseline(Base):
    """PR F.2 / F.3 — baseline utilisateur (géo, churn, fréquence, patterns temporels)."""

    __tablename__ = "auth_user_risk_baselines"
    __table_args__ = ({"schema": "public"},)

    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), primary_key=True)
    primary_country = Column(String(8), nullable=True)
    countries_json = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    frequent_ips_json = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    device_count_ema = Column(Float, nullable=False, server_default=text("1.0"))
    actions_per_hour_ema = Column(Float, nullable=False, server_default=text("0.0"))
    baseline_sample_count = Column(Integer, nullable=False, server_default=text("0"))
    # PR F.3 — agrégats affichables (Welford : état dans temporal_welford_json)
    avg_hour_of_day = Column(Float, nullable=True)
    std_hour_of_day = Column(Float, nullable=True)
    avg_weekday = Column(Float, nullable=True)
    std_weekday = Column(Float, nullable=True)
    avg_session_duration_sec = Column(Float, nullable=True)
    std_session_duration_sec = Column(Float, nullable=True)
    last_10_actions_types = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    temporal_welford_json = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("AdminUser", backref=backref("auth_user_risk_baseline", uselist=False))


class AuthRiskRule(Base):
    """PR F.4 — règles de risque dynamiques (conditions JSON, priorité)."""

    __tablename__ = "auth_risk_rules"
    __table_args__ = (
        Index("ix_auth_risk_rules_priority", "priority"),
        Index("ix_auth_risk_rules_enabled", "enabled"),
        Index("ix_auth_risk_rules_ruleset_active_priority", "ruleset", "is_active", "priority"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(128), nullable=True)
    priority = Column(Integer, nullable=False, server_default=text("100"))
    conditions = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    action = Column(String(16), nullable=False)
    enabled = Column(Boolean, nullable=False, server_default=text("true"))
    version = Column(Integer, nullable=False, server_default=text("1"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    ruleset = Column(String(64), nullable=False, server_default=text("'default'"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AuthUserIntentEvent(Base):
    """PR F.6 — journal d’actions pour détection d’intention (séquences suspectes)."""

    __tablename__ = "auth_user_intent_events"
    __table_args__ = (
        Index("ix_auth_user_intent_events_user_created", "user_id", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(128), nullable=False)
    action_type = Column(String(64), nullable=False)
    metadata_payload = Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("AdminUser", backref="auth_user_intent_events")


class AuthUserRiskFeatures(Base):
    """PR F.7 — vecteur de features + EMA pour écart pseudo-ML."""

    __tablename__ = "auth_user_risk_features"
    __table_args__ = ({"schema": "public"},)

    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), primary_key=True)
    features = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("AdminUser", backref=backref("auth_user_risk_features", uselist=False))


class AuthUserTemporalFeatures(Base):
    """PR F.7.2 — distributions temporelles + EMA débit (anomalies calendrier / transitions)."""

    __tablename__ = "auth_user_temporal_features"
    __table_args__ = ({"schema": "public"},)

    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), primary_key=True)
    hour_distribution = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    weekday_distribution = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    action_transition_matrix = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    ema_activity_drift = Column(Float, nullable=True)
    activity_rate_ema = Column(Float, nullable=True)
    sample_count = Column(Integer, nullable=False, server_default=text("0"))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("AdminUser", backref=backref("auth_user_temporal_features", uselist=False))


class AuthSecurityDecision(Base):
    """Journal des décisions du moteur de politique Zero Trust (audit / SIEM)."""

    __tablename__ = "auth_security_decisions"
    __table_args__ = (
        Index("ix_auth_security_decisions_user_id", "user_id"),
        Index("ix_auth_security_decisions_created_at", "created_at"),
        Index("ix_auth_security_decisions_action", "action"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("public.auth_sessions.id", ondelete="SET NULL"), nullable=True)
    device_id = Column(String(128), nullable=True)
    action = Column(String(256), nullable=False)
    resource = Column(String(512), nullable=False)
    allow = Column(Boolean, nullable=False)
    require_step_up = Column(Boolean, nullable=False, server_default=text("false"))
    deny_reason = Column(Text, nullable=True)
    policy_id = Column(String(128), nullable=False)
    context_snapshot_json = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthSecurityEvent(Base):
    """Événements de sécurité auth (observabilité, corrélation Phase 3.1)."""

    __tablename__ = "auth_security_events"
    __table_args__ = (
        Index("ix_auth_security_events_user_id", "user_id"),
        Index("ix_auth_security_events_device_id", "device_id"),
        Index("ix_auth_security_events_ip_address", "ip_address"),
        Index("ix_auth_security_events_created_at", "created_at"),
        Index("ix_auth_security_events_event_type", "event_type"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, nullable=True)
    device_id = Column(String(128), nullable=False)
    event_type = Column(String(128), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    metadata_payload = Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthDeviceReputation(Base):
    """Réputation agrégée par identité device (hash composite)."""

    __tablename__ = "auth_device_reputation"
    __table_args__ = ({"schema": "public"},)

    device_hash = Column(String(64), primary_key=True, nullable=False)
    global_risk_score = Column(Integer, nullable=False, server_default=text("0"))
    reputation_level = Column(String(16), nullable=False, server_default=text("'LOW'"))
    total_sessions = Column(Integer, nullable=False, server_default=text("0"))
    unique_user_count = Column(Integer, nullable=False, server_default=text("0"))
    unique_ip_count = Column(Integer, nullable=False, server_default=text("0"))
    suspicious_event_count = Column(Integer, nullable=False, server_default=text("0"))
    blocked_until = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AuthDeviceUsageEdge(Base):
    """Arête user ↔ device ↔ IP pour graphe et réputation."""

    __tablename__ = "auth_device_usage_edges"
    __table_args__ = (
        Index("ix_auth_device_usage_edges_device_hash", "device_hash"),
        Index("ix_auth_device_usage_edges_user_id", "user_id"),
        Index("ix_auth_device_usage_edges_created_at", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    device_hash = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.auth_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    ip_address = Column(String(45), nullable=True)
    event_type = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthDeviceBlacklist(Base):
    """Blocage explicite (jamais automatique au premier signal — réservé admin / policy)."""

    __tablename__ = "auth_device_blacklist"
    __table_args__ = (
        Index("ix_auth_device_blacklist_device_hash", "device_hash"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    device_hash = Column(String(64), nullable=False)
    reason = Column(String(512), nullable=False)
    blocked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)


class AuthDeviceGraphFinding(Base):
    """Findings persistés des analyses graphe (audit / SIEM)."""

    __tablename__ = "auth_device_graph_findings"
    __table_args__ = (
        Index("ix_auth_device_graph_findings_device_hash", "device_hash"),
        Index("ix_auth_device_graph_findings_created_at", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    device_hash = Column(String(64), nullable=True)
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    finding_type = Column(String(128), nullable=False)
    severity = Column(String(16), nullable=False)
    metadata_json = Column("metadata_json", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthDeviceAttestNonce(Base):
    """Nonce serveur pour App Attest / Play Integrity (challenge → assertion)."""

    __tablename__ = "auth_device_attest_nonces"
    __table_args__ = (
        Index("ix_auth_device_attest_nonces_expires_at", "expires_at"),
        {"schema": "public"},
    )

    nonce_hash = Column(String(64), primary_key=True, nullable=False)
    platform = Column(String(32), nullable=True)
    device_id_prefix = Column(String(16), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthDeviceAttestArtifact(Base):
    """Empreinte d’assertion / jeton integrity déjà acceptée (anti-rejeu)."""

    __tablename__ = "auth_device_attest_artifacts"
    __table_args__ = (
        Index("ix_auth_device_attest_artifacts_expires_at", "expires_at"),
        {"schema": "public"},
    )

    digest = Column(String(64), primary_key=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthSpentRefreshJti(Base):
    """JTIs de refresh déjà consommés (rotation / upgrade legacy) — détecte la réutilisation."""

    __tablename__ = "auth_spent_refresh_jti"
    __table_args__ = ({"schema": "public"},)

    jti = Column(String(64), primary_key=True, nullable=False)
    spent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthWebAuthnChallenge(Base):
    """Challenge WebAuthn temporaire (enregistrement / login) — anti-replay via TTL + suppression."""

    __tablename__ = "auth_webauthn_challenges"
    __table_args__ = (
        Index("ix_auth_webauthn_challenges_challenge_b64", "challenge_b64", unique=True),
        Index("ix_auth_webauthn_challenges_expires_at", "expires_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    challenge_b64 = Column(String(512), nullable=False)
    flow_type = Column(String(32), nullable=False)
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=True)
    identifier = Column(String(255), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthAdminEmailOtpChallenge(Base):
    """OTP e-mail jetable pour connexion admin (même session JWT que mot de passe / passkeys)."""

    __tablename__ = "auth_admin_email_otp_challenges"
    __table_args__ = (
        Index("uq_auth_admin_email_otp_email", "email_normalized", unique=True),
        Index("ix_auth_admin_email_otp_expires_at", "expires_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    email_normalized = Column(String(255), nullable=False)
    code_hash = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempt_count = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthMobileLoginOtpChallenge(Base):
    """OTP SMS jetable pour connexion admin par mobile (même JWT que e-mail OTP)."""

    __tablename__ = "auth_mobile_login_otp_challenges"
    __table_args__ = (
        Index("uq_auth_mobile_login_otp_phone", "phone_e164_normalized", unique=True),
        Index("ix_auth_mobile_login_otp_expires_at", "expires_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    phone_e164_normalized = Column(String(24), nullable=False)
    code_hash = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempt_count = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthPasskey(Base):
    """Credential WebAuthn (clé publique seulement côté serveur — Phase 3.2)."""

    __tablename__ = "auth_passkeys"
    __table_args__ = (
        Index("ix_auth_passkeys_user_id", "user_id"),
        Index("uq_auth_passkeys_credential_id_b64", "credential_id_b64", unique=True),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    credential_id_b64 = Column(String(512), nullable=False)
    public_key_b64 = Column(Text, nullable=False)
    sign_count = Column(BigInteger, nullable=False, server_default="0")
    transports_json = Column(JSONB, nullable=True)
    device_label = Column(String(255), nullable=True)
    aaguid = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("AdminUser", backref="auth_passkeys")


# ============================================================================
# Market Data Models
# ============================================================================

class MarketDataInstrument(Base):
    __tablename__ = "market_data_instruments"
    __table_args__ = (
        {"schema": "public"},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    asset_class = Column(String(20), nullable=False)  # "equity", "etf", "crypto"
    weekend_tradable = Column(String(10), nullable=False, server_default="false")  # "true" or "false" as string
    provider = Column(String(50), nullable=False, server_default="binance")
    provider_symbol = Column(String(50), nullable=True)
    is_active = Column(String(10), nullable=False, server_default="true")  # "true" or "false" as string
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    logo_filename = Column(String(100), nullable=True)  # e.g. "crypto_logos/btc.png", served at /media/...


class MarketDataBarD1(Base):
    __tablename__ = "market_data_bars_d1"
    __table_args__ = {"schema": "public"}
    
    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), primary_key=True, nullable=False, index=True)
    date = Column(Date, primary_key=True, nullable=False, index=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(BigInteger, nullable=False)
    source = Column(String(50), nullable=False, server_default="binance")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    
    instrument = relationship("MarketDataInstrument", backref="bars")


class MarketDataBar1m(Base):
    """Intraday 1-minute OHLCV candles (e.g. Binance)."""
    __tablename__ = "market_data_bars_1m"
    __table_args__ = {"schema": "public"}

    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), primary_key=True, nullable=False, index=True)
    open_time = Column(DateTime(timezone=True), primary_key=True, nullable=False, index=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    source = Column(String(50), nullable=False, server_default="binance")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    instrument = relationship("MarketDataInstrument", backref="bars_1m")


class MarketDataBar5m(Base):
    """Intraday 5-minute OHLCV candles (e.g. Binance)."""
    __tablename__ = "market_data_bars_5m"
    __table_args__ = {"schema": "public"}

    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), primary_key=True, nullable=False, index=True)
    open_time = Column(DateTime(timezone=True), primary_key=True, nullable=False, index=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    source = Column(String(50), nullable=False, server_default="binance")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    instrument = relationship("MarketDataInstrument", backref="bars_5m")


class MarketDataBar1h(Base):
    """1-hour OHLCV candles (e.g. Binance)."""
    __tablename__ = "market_data_bars_1h"
    __table_args__ = {"schema": "public"}

    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), primary_key=True, nullable=False, index=True)
    open_time = Column(DateTime(timezone=True), primary_key=True, nullable=False, index=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    source = Column(String(50), nullable=False, server_default="binance")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    instrument = relationship("MarketDataInstrument", backref="bars_1h")


class MarketDataBar4h(Base):
    """4-hour OHLCV candles (e.g. Binance)."""
    __tablename__ = "market_data_bars_4h"
    __table_args__ = {"schema": "public"}

    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), primary_key=True, nullable=False, index=True)
    open_time = Column(DateTime(timezone=True), primary_key=True, nullable=False, index=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    source = Column(String(50), nullable=False, server_default="binance")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    instrument = relationship("MarketDataInstrument", backref="bars_4h")


class MarketDataBar1d(Base):
    """1-day OHLCV candles (e.g. Binance)."""
    __tablename__ = "market_data_bars_1d"
    __table_args__ = {"schema": "public"}

    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), primary_key=True, nullable=False, index=True)
    open_time = Column(DateTime(timezone=True), primary_key=True, nullable=False, index=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    source = Column(String(50), nullable=False, server_default="binance")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    instrument = relationship("MarketDataInstrument", backref="bars_1d")


class MarketDataBar1w(Base):
    """1-week OHLCV candles (e.g. Binance)."""
    __tablename__ = "market_data_bars_1w"
    __table_args__ = {"schema": "public"}

    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), primary_key=True, nullable=False, index=True)
    open_time = Column(DateTime(timezone=True), primary_key=True, nullable=False, index=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    source = Column(String(50), nullable=False, server_default="binance")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    instrument = relationship("MarketDataInstrument", backref="bars_1w")


class MarketDataLatestQuote(Base):
    """Snapshot table: one row per instrument for latest quote (e.g. Binance ticker)."""
    __tablename__ = "market_data_latest_quotes"
    __table_args__ = {"schema": "public"}

    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), primary_key=True, nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    provider_symbol = Column(String(50), nullable=True)
    last_price = Column(Numeric(20, 8), nullable=False)
    bid_price = Column(Numeric(20, 8), nullable=True)
    ask_price = Column(Numeric(20, 8), nullable=True)
    volume = Column(Numeric(20, 8), nullable=True)
    quote_time = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    instrument = relationship("MarketDataInstrument", backref=backref("latest_quote", uselist=False))


class MarketDataBundle(Base):
    __tablename__ = "bundles"
    __table_args__ = (
        {"schema": "public"},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    asset_class = Column(String(20), nullable=True)
    type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(String(10), nullable=False, server_default="true")  # "true" or "false" as string
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    created_by_email = Column(String(255), nullable=True)


class BundleComponent(Base):
    __tablename__ = "bundle_components"
    __table_args__ = (
        {"schema": "public"},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    bundle_id = Column(Integer, ForeignKey("public.bundles.id"), nullable=False, index=True)
    component_type = Column(String(20), nullable=True)  # "instrument" or "bundle"
    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), nullable=True)
    child_bundle_id = Column(Integer, ForeignKey("public.bundles.id"), nullable=True)
    weight = Column(Numeric(10, 4), nullable=True)
    position_order = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    
    bundle = relationship("MarketDataBundle", foreign_keys=[bundle_id], backref="components")
    instrument = relationship("MarketDataInstrument", foreign_keys=[instrument_id], backref="bundle_components")
    child_bundle = relationship("MarketDataBundle", foreign_keys=[child_bundle_id])


# ============================================================================
# Backtest Models
# ============================================================================

class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (
        {"schema": "public"},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=True)
    created_by_user_id = Column(Integer, nullable=True)  # No FK, quant DB isolated
    created_by_email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    effective_start_date = Column(Date, nullable=True)
    effective_end_date = Column(Date, nullable=True)
    rebalance = Column(String(20), nullable=False)  # "daily", "weekly", "monthly"
    strategy_type = Column(String(50), nullable=False)  # "equal_weight", "momentum"
    strategy_params_json = Column(JSON, nullable=True)
    fees_bps = Column(Numeric(10, 4), nullable=False, server_default="0.0")
    slippage_bps = Column(Numeric(10, 4), nullable=False, server_default="0.0")
    allow_weekend_trading = Column(String(10), nullable=False, server_default="true")  # "true" or "false" as string
    instrument_ids_json = Column(JSON, nullable=False)  # Array of instrument IDs
    bundle_id = Column(String(36), nullable=True)  # Optional bundle ID (stored as string, but can reference bundles.id)
    status = Column(String(20), nullable=False, server_default="PENDING")  # "PENDING", "SUCCESS", "FAILED"
    error_message = Column(Text, nullable=True)


class BacktestPortfolioSeries(Base):
    __tablename__ = "backtest_portfolio_series"
    __table_args__ = (
        {"schema": "public"},
    )
    
    run_id = Column(Integer, ForeignKey("public.backtest_runs.id"), primary_key=True, nullable=False, index=True)
    date = Column(Date, primary_key=True, nullable=False, index=True)
    nav_base100 = Column(Numeric(20, 8), nullable=False)
    portfolio_return = Column(Numeric(20, 8), nullable=False)
    drawdown = Column(Numeric(20, 8), nullable=False)
    turnover = Column(Numeric(20, 8), nullable=False)
    costs = Column(Numeric(20, 8), nullable=False)
    weights_json = Column(JSON, nullable=True)  # Dict of instrument_id: weight
    tradable_json = Column(JSON, nullable=True)  # Dict of instrument_id: tradable (bool)
    
    run = relationship("BacktestRun", backref="portfolio_series")


class BacktestInstrumentSeries(Base):
    __tablename__ = "backtest_instrument_series"
    __table_args__ = (
        {"schema": "public"},
    )
    
    run_id = Column(Integer, ForeignKey("public.backtest_runs.id"), primary_key=True, nullable=False, index=True)
    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), primary_key=True, nullable=False, index=True)
    date = Column(Date, primary_key=True, nullable=False, index=True)
    base100 = Column(Numeric(20, 8), nullable=False)
    instrument_return = Column(Numeric(20, 8), nullable=True)
    
    run = relationship("BacktestRun", backref="instrument_series")
    instrument = relationship("MarketDataInstrument", backref="backtest_series")


class BacktestMetrics(Base):
    __tablename__ = "backtest_metrics"
    __table_args__ = (
        {"schema": "public"},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("public.backtest_runs.id"), nullable=False, index=True)
    scope = Column(String(20), nullable=False)  # "portfolio" or "instrument"
    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), nullable=True, index=True)
    key = Column(String(50), nullable=False)  # Metric name: "cagr", "sharpe", etc.
    value = Column(Numeric(20, 8), nullable=False)
    
    run = relationship("BacktestRun", backref="metrics")
    instrument = relationship("MarketDataInstrument", backref="metrics")


class FieldDefinition(Base):
    __tablename__ = "field_definitions"
    __table_args__ = (
        Index('ix_field_definitions_category', 'category'),
        {"schema": "public"},
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    field_name_en = Column(Text, nullable=False)
    field_type = Column(Text, nullable=False)
    category = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default='true')
    ui_label = Column(Text, nullable=True)
    component_type_default = Column(Text, nullable=True)
    required_default = Column(Boolean, nullable=True)
    policy_scope = Column(Text, nullable=True)
    options_json = Column(JSONB(astext_type=Text), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Person(Base):
    __tablename__ = "persons"
    __table_args__ = (
        Index('ix_persons_profile_json', 'profile_json', postgresql_using='gin'),
        Index('ix_persons_jurisdiction', 'jurisdiction'),
        {"schema": "public"},
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    status = Column(Text, nullable=False, server_default='active')
    jurisdiction = Column(Text, nullable=True)
    profile_json = Column(JSONB(astext_type=Text), nullable=False, server_default='{}')
    client_id = Column(UUID(as_uuid=True), unique=True, nullable=True)
    kyc_status = Column(Text, nullable=False, server_default='not_started')
    login_frozen = Column(Boolean, nullable=False, server_default=text("false"))
    # PARTIAL / ACTIVE — aligné sur derive_account_state (passcode ACK + pe_clients) ; backfill migration 129.
    account_state = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    trading_client = relationship(
        "Client",
        back_populates="person",
        uselist=False,
        foreign_keys="[Client.person_id]",
    )

    two_factor_challenges = relationship(
        "TwoFactorChallenge",
        back_populates="person",
        order_by="TwoFactorChallenge.created_at.desc()",
    )

    external_identities = relationship(
        "PersonExternalIdentity",
        back_populates="person",
        lazy="dynamic",
    )
    crypto_wallets_user_controlled = relationship(
        "PersonCryptoWallet",
        back_populates="person",
        lazy="dynamic",
    )


class PersonExternalIdentity(Base):
    """Identité externe (Privy, etc.) — toujours liée à ``persons.id`` (pas ``admin_users``)."""

    __tablename__ = "person_external_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "external_subject",
            name="uq_person_external_identities_provider_subject",
        ),
        Index("ix_person_external_identities_person_id", "person_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider = Column(Text, nullable=False)
    external_subject = Column(Text, nullable=False)
    external_email = Column(Text, nullable=True)
    external_phone = Column(Text, nullable=True)
    metadata_json = Column(JSONB(astext_type=Text), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    person = relationship("Person", back_populates="external_identities")


class PersonCryptoWallet(Base):
    """Wallet non-custodial / user-controlled — distinct de ``crypto_positions`` et custody interne."""

    __tablename__ = "person_crypto_wallets"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "chain_type",
            "address",
            name="uq_person_crypto_wallets_provider_chain_address",
        ),
        Index("ix_person_crypto_wallets_person_id", "person_id"),
        Index("ix_person_crypto_wallets_pe_client_id", "pe_client_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    pe_client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider = Column(Text, nullable=False)
    wallet_type = Column(Text, nullable=False)
    chain_type = Column(Text, nullable=False)
    chain_id = Column(Integer, nullable=True)
    address = Column(Text, nullable=False)
    is_primary = Column(Boolean, nullable=False, server_default=text("true"))
    metadata_json = Column(JSONB(astext_type=Text), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    person = relationship("Person", back_populates="crypto_wallets_user_controlled")


class TwoFactorChallenge(Base):
    """SMS/email OTP and TOTP verification challenges (reusable via purpose)."""

    __tablename__ = "two_factor_challenges"
    __table_args__ = (
        Index("ix_two_factor_challenges_person_id", "person_id"),
        Index("ix_two_factor_challenges_status", "status"),
        Index("ix_two_factor_challenges_expires_at", "expires_at"),
        Index("ix_two_factor_challenges_person_created", "person_id", "created_at"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    person_id = Column(UUID(as_uuid=True), ForeignKey("public.persons.id", ondelete="CASCADE"), nullable=False)
    channel = Column(Text, nullable=False)
    target = Column(Text, nullable=True)
    code_hash = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False, server_default="0")
    status = Column(Text, nullable=False, server_default="pending")
    purpose = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    source_ip = Column(Text, nullable=True)

    person = relationship("Person", back_populates="two_factor_challenges")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index('ix_audit_events_person_id_created_at', 'person_id', 'created_at'),
        Index('ix_audit_events_event_type', 'event_type'),
        Index('ix_audit_events_correlation_id', 'correlation_id'),
        Index('ix_audit_events_payload', 'payload', postgresql_using='gin'),
        {"schema": "public"},
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    person_id = Column(UUID(as_uuid=True), ForeignKey('public.persons.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(Text, nullable=False)
    actor_type = Column(Text, nullable=False)  # user|admin|system|provider
    actor_id = Column(Text, nullable=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=True)
    payload = Column(JSONB(astext_type=Text), nullable=False, server_default='{}')
    schema_version = Column(Integer, nullable=False, server_default='1')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    person = relationship("Person", backref="audit_events")


class JurisdictionConfig(Base):
    __tablename__ = "jurisdiction_configs"
    __table_args__ = (
        UniqueConstraint('jurisdiction', 'purpose', 'version', name='uq_jurisdiction_configs_jurisdiction_purpose_version'),
        Index('ix_jurisdiction_configs_jurisdiction_purpose_status', 'jurisdiction', 'purpose', 'status'),
        Index('ix_jurisdiction_configs_config_json', 'config_json', postgresql_using='gin'),
        {"schema": "public"},
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    jurisdiction = Column(Text, nullable=False)
    purpose = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(Text, nullable=False)  # draft|active|archived
    config_json = Column(JSONB(astext_type=Text), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index('ix_documents_person_id_created_at', 'person_id', 'created_at'),
        Index('ix_documents_metadata_json', 'metadata_json', postgresql_using='gin'),
        {"schema": "public"},
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    person_id = Column(UUID(as_uuid=True), ForeignKey('public.persons.id', ondelete='CASCADE'), nullable=False)
    doc_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    storage_provider = Column(Text, nullable=False)
    storage_bucket = Column(Text, nullable=False)
    storage_key = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    sha256 = Column(Text, nullable=False)
    metadata_json = Column(JSONB(astext_type=Text), nullable=False, server_default='{}')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    person = relationship("Person", backref="documents")


# ============================================================================
# Chatbot Épargne (Bot IA) — spec AUDIT_ET_ARCHITECTURE_BOT_EPARGNE_WEALTHTECH
# ============================================================================

class ChatbotSession(Base):
    __tablename__ = "chatbot_sessions"
    __table_args__ = (
        Index("ix_chatbot_sessions_created_at", "created_at"),
        Index("ix_chatbot_sessions_expires_at", "expires_at"),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    ip_hash = Column(String(64), nullable=True)  # SHA256 hash of IP address
    user_agent_hash = Column(String(64), nullable=True)  # SHA256 hash of user agent
    conversation_summary = Column(Text, nullable=True)
    conversation_facts = Column(JSONB(astext_type=Text), nullable=True, server_default="[]")
    last_next_question_id = Column(Text, nullable=True)


class ChatbotProfile(Base):
    __tablename__ = "chatbot_profiles"
    __table_args__ = (
        Index("ix_chatbot_profiles_session_id", "session_id"),
        Index("ix_chatbot_profiles_session_version", "session_id", "version"),
        Index("ix_chatbot_profiles_created_at", "created_at"),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("public.chatbot_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, server_default="1")
    payload = Column(JSONB(astext_type=Text), nullable=False, server_default="{}")
    completeness_score = Column(Numeric(5, 4), nullable=False, server_default="0")  # 0–1
    missing_fields = Column(JSONB(astext_type=Text), nullable=False, server_default="[]")  # array of strings
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    session = relationship("ChatbotSession", backref="profiles")


class ChatbotConversationTurn(Base):
    __tablename__ = "chatbot_conversation_turns"
    __table_args__ = (
        Index("ix_chatbot_turns_session_id", "session_id"),
        Index("ix_chatbot_turns_session_created", "session_id", "created_at"),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("public.chatbot_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    turn_index = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    extracted_json = Column(JSONB(astext_type=Text), nullable=True)
    profile_snapshot_id = Column(UUID(as_uuid=True), ForeignKey("public.chatbot_profiles.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    session = relationship("ChatbotSession", backref="turns")


class ChatbotAuditEvent(Base):
    __tablename__ = "chatbot_audit_events"
    __table_args__ = (
        Index("ix_chatbot_audit_session_id", "session_id"),
        Index("ix_chatbot_audit_session_created", "session_id", "created_at"),
        Index("ix_chatbot_audit_event_type", "event_type"),
        Index("ix_chatbot_audit_payload", "payload", postgresql_using="gin"),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("public.chatbot_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(Text, nullable=False)
    payload = Column(JSONB(astext_type=Text), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    session = relationship("ChatbotSession", backref="audit_events")


class ChatbotPortfolioProposal(Base):
    __tablename__ = "chatbot_portfolio_proposals"
    __table_args__ = (
        Index("ix_chatbot_proposals_profile_id", "profile_id"),
        Index("ix_chatbot_proposals_created_at", "created_at"),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("public.chatbot_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    allocation = Column(JSONB(astext_type=Text), nullable=False, server_default="[]")
    rationale = Column(Text, nullable=True)
    disclaimers = Column(JSONB(astext_type=Text), nullable=False, server_default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    profile = relationship("ChatbotProfile", backref="portfolio_proposals")


class ChatbotPromptVersion(Base):
    __tablename__ = "chatbot_prompt_versions"
    __table_args__ = (
        Index("ix_chatbot_prompt_name_hash", "name", "hash"),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(100), nullable=False)
    hash = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ============================================================================
# Assistance « sur mesure » (mobile Flutter Search Screen) — MVP D.1.1
# Conversations & messages persistés par client (pe_clients), distinct du
# `chatbot_epargne` (funnel projet épargne avec sessions anonymes).
# ============================================================================

class AssistanceConversation(Base):
    __tablename__ = "assistance_conversations"
    __table_args__ = (
        Index(
            "ix_assistance_conversations_client_last",
            "client_id",
            "last_message_at",
        ),
        Index(
            "ix_assistance_conversations_client_status",
            "client_id",
            "status",
        ),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, server_default="active")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    # D.1.4.2 — indicateur de réponse assistant non lue.
    last_assistant_message_at = Column(DateTime(timezone=True), nullable=True)
    last_read_at = Column(DateTime(timezone=True), nullable=True)
    # ── Palier 2 D.2 — Mémoire long-terme (migration 146) ─────────────
    # Résumé narratif (rolling summary) maintenu par services.assistance.memory.
    conversation_summary = Column(Text, nullable=True)
    # Faits structurés extraits ([{type, value, confidence, evidence, source_turn}]).
    conversation_facts = Column(
        JSONB(astext_type=Text), nullable=False, server_default="[]"
    )
    # turn_index du dernier tour absorbé par `conversation_summary`.
    summarized_until_turn = Column(Integer, nullable=True)
    # Horodatage de la dernière consolidation mémoire (debug / diag).
    summary_updated_at = Column(DateTime(timezone=True), nullable=True)
    # ── Phase 2 wiki v1.4 patch — Slot « topic en cours » (migration 150) ──
    # Sujet actif de la conversation à l'instant t (vs. recent_turns qui
    # sont les N derniers messages bruts, et conversation_summary qui est
    # une narration). Set automatiquement par les tools experts qui
    # ancrent un sujet (`show_bundle_detail`, `show_instrument_card`,
    # etc.) et lu par le router pour stabiliser les follow-ups.
    # Schéma libre : cf. `services.assistance.conversation_topic`.
    current_topic = Column(JSONB(astext_type=Text), nullable=True)


class AssistanceMessage(Base):
    __tablename__ = "assistance_messages"
    __table_args__ = (
        Index(
            "ix_assistance_messages_conversation_created",
            "conversation_id",
            "created_at",
        ),
        UniqueConstraint(
            "conversation_id",
            "turn_index",
            name="uq_assistance_messages_conversation_turn",
        ),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.assistance_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_index = Column(Integer, nullable=False)
    role = Column(String(16), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Multi-agents Phase 1 (cf. docs/arquantix/MULTI_AGENTS.md, migration 147).
    # `agent_used`     : identifiant de l'agent ayant produit le message
    #                    assistant (`default`, `compliance`, `advisor`,
    #                    `product`, `market`, `router`). NULL pour les
    #                    messages user et les anciens messages assistant.
    # `message_type`   : `'text'` (défaut, bulle Markdown) ou `'choices'`
    #                    (QCM poussé par le router en cas d'indécision).
    # `message_payload`: structure JSON quand `message_type != 'text'`.
    agent_used = Column(String(32), nullable=True)
    message_type = Column(
        String(16), nullable=False, server_default="text"
    )
    message_payload = Column(JSONB, nullable=True)


class AssistanceActionDraft(Base):
    """Brouillon transactionnel CAL (migration 154) — audit, pas d'exécution métier."""

    __tablename__ = "assistance_action_drafts"
    __table_args__ = (
        Index(
            "ix_assistance_action_drafts_conversation_id",
            "conversation_id",
        ),
        Index(
            "ix_assistance_action_drafts_client_created",
            "client_id",
            "created_at",
            postgresql_ops={"created_at": "DESC NULLS LAST"},
        ),
        {"schema": "public"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.assistance_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, server_default="draft")
    payload = Column(
        JSONB(astext_type=Text()),
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AssistanceActionPlaybook(Base):
    """Catalogue déclaratif des parcours CAL (édition admin, injection agent product)."""

    __tablename__ = "assistance_action_playbooks"
    __table_args__ = (
        Index(
            "ix_assistance_action_playbooks_enabled_sort",
            "is_enabled",
            "sort_order",
        ),
        Index(
            "uq_assistance_action_playbooks_action_key",
            "action_key",
            unique=True,
        ),
        {"schema": "public"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    action_key = Column(String(64), nullable=False)
    label = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    transaction_kind = Column(String(32), nullable=False)
    agent_id = Column(String(32), nullable=False, server_default="product")
    definition = Column(
        JSONB(astext_type=Text()),
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    is_enabled = Column(Boolean, nullable=False, server_default=text("true"))
    sort_order = Column(Integer, nullable=False, server_default="0")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AssistanceAgentDecision(Base):
    """Audit trail des décisions agentiques (Phase 2a multi-agents).

    Une ligne par tool call exécuté par le runtime agentique
    (cf. `docs/arquantix/MULTI_AGENTS_RUNTIME.md` § 4 + migration 148).

    Champs sensibles :
      - `reasoning_summary` : passe par le sanitizer TIPPING_OFF_BLACKLIST
        avant écriture (discipline applicative protégée par les tests CI
        bloquants `test_assistance_tipping_off_*`).
      - `autonomy_level` ∈ {'L0','L1','L2','L3'} (CHECK contraint en SQL).
      - `review_status`   ∈ {'auto','pending','approved','rejected'}
        (CHECK contraint en SQL).
    """

    __tablename__ = "assistance_agent_decisions"
    __table_args__ = (
        Index(
            "ix_assistance_agent_decisions_conv_iter",
            "conversation_id",
            "iteration",
        ),
        Index(
            "ix_assistance_agent_decisions_agent_created",
            "agent_id",
            "created_at",
        ),
        Index("ix_assistance_agent_decisions_tool_name", "tool_name"),
        Index(
            "ix_assistance_agent_decisions_autonomy_level", "autonomy_level"
        ),
        Index(
            "ix_assistance_agent_decisions_target_client",
            "target_client_id",
            "created_at",
        ),
        # Index partiel `ix_assistance_agent_decisions_review_pending` créé
        # via Alembic (postgresql_where) — non déclaré ici car SQLAlchemy
        # autoload-only.
        {"schema": "public"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "public.assistance_conversations.id", ondelete="CASCADE"
        ),
        nullable=False,
    )
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.assistance_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id = Column(String(32), nullable=False)
    iteration = Column(SmallInteger, nullable=False)
    tool_name = Column(String(64), nullable=False)
    autonomy_level = Column(String(4), nullable=False)
    arguments_json = Column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    result_summary = Column(JSONB, nullable=True)
    proposed_action = Column(String(64), nullable=True)
    target_client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="SET NULL"),
        nullable=True,
    )
    reasoning_summary = Column(Text, nullable=True)
    review_status = Column(
        String(16), nullable=False, server_default="auto"
    )
    reviewed_by = Column(
        Integer,
        # `admin_users` n'utilise PAS `schema="public"` côté SQLAlchemy
        # (cf. ligne 128). FK string sans préfixe pour matcher le mapping.
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_code = Column(String(32), nullable=True)
    correlation_id = Column(String(64), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Cognitive Bot v4 — Lot 6 (2026-05-04) — colonnes dénormalisées
    # extraites depuis ``arguments_json->'cognitive_state'`` et
    # ``arguments_json->'objective'`` pour permettre des index natifs
    # (analytics funnel) et la lecture par des outils tiers (Metabase).
    # ``arguments_json`` reste la **source de vérité** (audit complet) ;
    # ces colonnes sont remplies en double-write par le runtime
    # (`service._persist_router_decision`) — cf. migration 152 +
    # ``COGNITIVE_BOT.md`` §11. Toutes nullable : pas de contrainte CHECK
    # pour ne pas figer les enums (V2 = classifieur ML potentiel).
    emotional_intent = Column(String(32), nullable=True)
    conversation_stage = Column(String(16), nullable=True)
    knowledge_level = Column(String(8), nullable=True)
    trust_level = Column(Float, nullable=True)
    primary_goal = Column(String(16), nullable=True)
    next_best_action = Column(String(20), nullable=True)


class AssistanceClientDiscoveryProject(Base):
    """Cognitive Bot v4 — Lot 7 (2026-05-04). Projet client extrait par
    le ``client_discovery_extractor`` (achat maison, retraite, vacances…).

    Lié à la **personne** (FK ``persons.id``) plus qu'au ``pe_clients``
    pour permettre la mémoire **cross-conversation** (un même projet
    peut être évoqué dans plusieurs conv). ``conversation_id_source``
    trace la conv où le projet a été détecté pour la première fois.

    Cf. migration 153 + ``CLIENT_DISCOVERY.md``.
    """

    __tablename__ = "assistance_client_discovery_projects"
    __table_args__ = (
        # Les index partiels sont créés en Alembic (pas exprimables ici).
        {"schema": "public"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id_source = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "public.assistance_conversations.id", ondelete="SET NULL"
        ),
        nullable=True,
    )
    label = Column(String(80), nullable=False)
    # ``status`` ∈ {active, paused, completed, abandoned}. Pas de CHECK
    # SQL pour laisser respirer (cf. migration 153).
    status = Column(String(16), nullable=False, server_default="active")
    confidence = Column(Float, nullable=True)
    parameters = Column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at_turn = Column(Integer, nullable=True)
    last_touched_at_turn = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AssistanceFloatingParameter(Base):
    """Cognitive Bot v4 — Lot 7. Paramètre extrait par le discovery
    extractor mais non encore attribué à un projet.

    Cas typique : le user dit « 4 ans » sans nommer le projet, on
    stocke en floating et on demande clarification au prochain tour.
    Cf. ``CLIENT_DISCOVERY.md`` — règles d'attribution strictes.
    """

    __tablename__ = "assistance_floating_parameters"
    __table_args__ = ({"schema": "public"},)

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "public.assistance_conversations.id", ondelete="CASCADE"
        ),
        nullable=False,
    )
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    parameter_kind = Column(String(32), nullable=False)
    parameter_value = Column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # ``status`` ∈ {pending_attribution, attributed, discarded}.
    status = Column(
        String(24), nullable=False, server_default="pending_attribution"
    )
    attributed_project_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "public.assistance_client_discovery_projects.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    created_at_turn = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class ProductKnowledge(Base):
    """Base de connaissances factuelle de l'agent `product` (Phase 2c).

    Lue par le tool L0 `read_product_knowledge(slug)` pour ramener un
    contenu canonique court (200-500 mots) que l'agent `product` peut
    citer ou paraphraser. Source de vérité unique : pas de duplication
    LLM, donc pas d'hallucination sur les délais réglementaires.

    Phase 5 (RAG) substituera ce seed manuel par une ingestion
    vectorielle des fiches produit officielles depuis le CMS. La table
    reste alors pertinente pour les FAQ canoniques courtes
    (« délai SEPA », etc.) qui n'ont pas besoin du RAG.
    """

    __tablename__ = "product_knowledge"
    __table_args__ = (
        Index("ix_product_knowledge_topic", "topic"),
        # `ix_product_knowledge_active` est partiel (`WHERE is_active`)
        # — créé via Alembic uniquement.
        {"schema": "public"},
    )

    slug = Column(String(80), primary_key=True, nullable=False)
    topic = Column(String(40), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    metadata_json = Column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    is_active = Column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Registration Flow Engine (Phase 2A)
# ---------------------------------------------------------------------------

class RegistrationJurisdiction(Base):
    __tablename__ = "registration_jurisdictions"
    __table_args__ = ({"schema": "public"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    entity_name = Column(Text, nullable=True)
    default_language = Column(Text, nullable=False, server_default="en")
    supported_languages = Column(JSONB(astext_type=Text), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    flows = relationship("RegistrationFlow", back_populates="jurisdiction", order_by="RegistrationFlow.version.desc()")


class CountryDirectory(Base):
    """Global country reference (ISO2, dial codes, display names)."""

    __tablename__ = "country_directory"
    __table_args__ = ({"schema": "public"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    iso2 = Column(Text, nullable=False, unique=True)
    iso3 = Column(Text, nullable=False, unique=True)
    display_name_en = Column(Text, nullable=False)
    display_name_fr = Column(Text, nullable=False)
    phone_country_code = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class JurisdictionCountryPolicy(Base):
    """Per-jurisdiction allowlists for phone calling country and residence country."""

    __tablename__ = "jurisdiction_country_policies"
    __table_args__ = (
        UniqueConstraint("jurisdiction_code", "country_iso2", name="uq_jcp_jurisdiction_country"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction_code = Column(Text, nullable=False, index=True)
    country_iso2 = Column(Text, ForeignKey("public.country_directory.iso2", ondelete="CASCADE"), nullable=False)
    allow_residence = Column(Boolean, nullable=False, server_default="false")
    allow_phone_country_code = Column(Boolean, nullable=False, server_default="false")
    allow_nationality = Column(Boolean, nullable=False, server_default="false")
    is_default_residence = Column(Boolean, nullable=False, server_default="false")
    is_default_phone = Column(Boolean, nullable=False, server_default="false")
    position = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    country = relationship("CountryDirectory", foreign_keys=[country_iso2])


class JurisdictionPolicySettings(Base):
    """Per-jurisdiction knobs for country policies (defaults, phone inheritance)."""

    __tablename__ = "jurisdiction_policy_settings"
    __table_args__ = (
        UniqueConstraint("jurisdiction_code", name="uq_jurisdiction_policy_settings_code"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction_code = Column(Text, nullable=False, unique=True)
    inherit_phone_countries_from_residence = Column(
        Boolean, nullable=False, server_default="false"
    )
    default_residence_iso2 = Column(
        Text, ForeignKey("public.country_directory.iso2", ondelete="SET NULL"), nullable=True
    )
    default_phone_iso2 = Column(
        Text, ForeignKey("public.country_directory.iso2", ondelete="SET NULL"), nullable=True
    )
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class RegistrationFlow(Base):
    __tablename__ = "registration_flows"
    __table_args__ = (
        UniqueConstraint("jurisdiction_id", "entrypoint_type", "version", name="uq_reg_flow_jurisdiction_entry_version"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_jurisdictions.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, server_default="1")
    status = Column(Text, nullable=False, server_default="draft")
    entrypoint_type = Column(Text, nullable=False, server_default="individual")
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    jurisdiction = relationship("RegistrationJurisdiction", back_populates="flows")
    steps = relationship("RegistrationFlowStep", back_populates="flow", order_by="RegistrationFlowStep.position")


class RegistrationFlowStep(Base):
    __tablename__ = "registration_flow_steps"
    __table_args__ = (
        UniqueConstraint("flow_id", "step_key", name="uq_reg_step_flow_key"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_flows.id", ondelete="CASCADE"), nullable=False)
    step_key = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    title_i18n = Column(JSONB(astext_type=Text), nullable=True)
    description = Column(Text, nullable=True)
    description_i18n = Column(JSONB(astext_type=Text), nullable=True)
    position = Column(Integer, nullable=False, server_default="0")
    is_optional = Column(Boolean, nullable=False, server_default="false")
    is_blocking = Column(Boolean, nullable=False, server_default="true")
    visibility_rule_json = Column(JSONB(astext_type=Text), nullable=True)
    completion_rule_json = Column(JSONB(astext_type=Text), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    flow = relationship("RegistrationFlow", back_populates="steps")
    screens = relationship(
        "RegistrationStepScreen",
        back_populates="step",
        order_by="RegistrationStepScreen.position",
        cascade="all, delete-orphan",
    )


class RegistrationStepScreen(Base):
    __tablename__ = "registration_step_screens"
    __table_args__ = (
        UniqueConstraint("step_id", "screen_key", name="uq_reg_screen_step_key"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_flow_steps.id", ondelete="CASCADE"), nullable=False)
    screen_key = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    title_i18n = Column(JSONB(astext_type=Text), nullable=True)
    subtitle = Column(Text, nullable=True)
    subtitle_i18n = Column(JSONB(astext_type=Text), nullable=True)
    button_label = Column(Text, nullable=True)
    button_label_i18n = Column(JSONB(astext_type=Text), nullable=True)
    position = Column(Integer, nullable=False, server_default="0")
    layout_type = Column(Text, nullable=False, server_default="form")
    config_json = Column(JSONB(astext_type=Text), nullable=True)
    screen_type = Column(Text, nullable=False, server_default="form")
    interaction_type = Column(Text, nullable=True)
    interaction_config_json = Column(JSONB(astext_type=Text), nullable=True)
    visibility_rule_json = Column(JSONB(astext_type=Text), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    step = relationship("RegistrationFlowStep", back_populates="screens")
    components = relationship(
        "RegistrationScreenComponent",
        back_populates="screen",
        order_by="RegistrationScreenComponent.position",
        cascade="all, delete-orphan",
    )


class RegistrationScreenComponent(Base):
    __tablename__ = "registration_screen_components"
    __table_args__ = (
        UniqueConstraint("screen_id", "component_key", name="uq_reg_component_screen_key"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    screen_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_step_screens.id", ondelete="CASCADE"), nullable=False)
    component_type = Column(Text, nullable=False)
    component_key = Column(Text, nullable=False)
    position = Column(Integer, nullable=False, server_default="0")
    props_json = Column(JSONB(astext_type=Text), nullable=True)
    binding_slug = Column(Text, nullable=True)
    field_definition_id = Column(UUID(as_uuid=True), ForeignKey("public.field_definitions.id"), nullable=True)
    visibility_rule_json = Column(JSONB(astext_type=Text), nullable=True)
    validation_rule_json = Column(JSONB(astext_type=Text), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    screen = relationship("RegistrationStepScreen", back_populates="components")
    field_definition = relationship("FieldDefinition", foreign_keys=[field_definition_id])


class RegistrationExecutionEvent(Base):
    """Append-only execution / audit timeline for a registration session (Phase A)."""

    __tablename__ = "registration_execution_events"
    __table_args__ = (
        Index("ix_reg_exec_events_session_id", "session_id"),
        Index("ix_reg_exec_events_flow_id", "flow_id"),
        Index("ix_reg_exec_events_created_at", "created_at"),
        Index("ix_reg_exec_events_event_type", "event_type"),
        Index("ix_reg_exec_events_person_id", "person_id"),
        Index("ix_reg_exec_events_client_id", "client_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_sessions.id", ondelete="CASCADE"), nullable=False)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_flows.id", ondelete="SET NULL"), nullable=True)
    flow_version = Column(Integer, nullable=True)
    step_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_flow_steps.id", ondelete="SET NULL"), nullable=True)
    screen_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_step_screens.id", ondelete="SET NULL"), nullable=True)
    component_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_screen_components.id", ondelete="SET NULL"), nullable=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("public.persons.id", ondelete="SET NULL"), nullable=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("public.pe_clients.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(Text, nullable=False)
    event_source = Column(Text, nullable=False, server_default="runtime")
    event_status = Column(Text, nullable=True)
    payload_json = Column(JSONB(astext_type=Text), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    session = relationship("RegistrationSession", back_populates="execution_events")


class RegistrationSession(Base):
    __tablename__ = "registration_sessions"
    __table_args__ = (
        Index("ix_reg_session_person", "person_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_jurisdictions.id"), nullable=False)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_flows.id"), nullable=False)
    flow_version = Column(Integer, nullable=False, server_default="1")
    person_id = Column(UUID(as_uuid=True), ForeignKey("public.persons.id"), nullable=True)
    client_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(Text, nullable=False, server_default="in_progress")
    current_step_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_flow_steps.id"), nullable=True)
    current_screen_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_step_screens.id"), nullable=True)
    progress_percent = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    jurisdiction = relationship("RegistrationJurisdiction")
    flow = relationship("RegistrationFlow")
    current_step = relationship("RegistrationFlowStep", foreign_keys=[current_step_id])
    current_screen = relationship("RegistrationStepScreen", foreign_keys=[current_screen_id])
    data_entries = relationship("RegistrationSessionData", back_populates="session", order_by="RegistrationSessionData.updated_at.desc()")
    step_states = relationship("RegistrationSessionStep", back_populates="session", order_by="RegistrationSessionStep.started_at")
    execution_events = relationship(
        "RegistrationExecutionEvent",
        back_populates="session",
        order_by="RegistrationExecutionEvent.created_at",
    )


class RegistrationSessionData(Base):
    __tablename__ = "registration_session_data"
    __table_args__ = (
        UniqueConstraint("session_id", "field_slug", name="uq_reg_session_data_slug"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_sessions.id", ondelete="CASCADE"), nullable=False)
    field_slug = Column(Text, nullable=False)
    value_json = Column(JSONB(astext_type=Text), nullable=True)
    source = Column(Text, nullable=False, server_default="user_input")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    session = relationship("RegistrationSession", back_populates="data_entries")


class RegistrationSessionStep(Base):
    __tablename__ = "registration_session_steps"
    __table_args__ = (
        UniqueConstraint("session_id", "step_id", name="uq_reg_session_step"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_sessions.id", ondelete="CASCADE"), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_flow_steps.id"), nullable=False)
    status = Column(Text, nullable=False, server_default="not_started")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    skipped_at = Column(DateTime(timezone=True), nullable=True)
    last_screen_id = Column(UUID(as_uuid=True), ForeignKey("public.registration_step_screens.id"), nullable=True)
    metadata_json = Column(JSONB(astext_type=Text), nullable=True)

    session = relationship("RegistrationSession", back_populates="step_states")
    step = relationship("RegistrationFlowStep")


class RegistrationRuntimeSetting(Base):
    __tablename__ = "registration_runtime_settings"
    __table_args__ = ({"schema": "public"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    current_jurisdiction_code = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


# Presentation decks / templates (registers ORM mappers + Alembic metadata)
import services.presentations.models as _presentation_deck_models  # noqa: F401, E402

# Operation statement PDF snapshots (PR5)
import services.test_clients.operation_statement_snapshot_model as _operation_statement_snapshots  # noqa: F401, E402


# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)


# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

