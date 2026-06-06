"""Schémas Pydantic pour l’API mobile (bootstrap, profil, wallet). Le dossier `test_clients` est un nom historique."""
from datetime import datetime
from typing import Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

class BootstrapClientPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: Optional[str] = None
    status: str
    kyc_status: str
    reference_currency: str = "EUR"
    initials: str = "?"


class BootstrapResponse(BaseModel):
    client: BootstrapClientPayload


class MobileProfilePersonalSection(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None


class MobileProfileAddressSection(BaseModel):
    line1: Optional[str] = None
    line2: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class MobileProfileIdentitySection(BaseModel):
    document_type: Optional[str] = None
    document_number_masked: Optional[str] = None
    document_expiry: Optional[str] = None


class MobileProfileContactSection(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None


class MobileContactEmailChangeSection(BaseModel):
    pending_email: Optional[str] = None
    status: Optional[str] = None  # pending | confirmed
    requested_at: Optional[str] = None
    confirmed_at: Optional[str] = None


class ContactEmailRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)


class ContactEmailConfirmRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    privy_access_token: str = Field(..., min_length=1)


class ContactEmailConfirmResponse(BaseModel):
    email: str
    status: str = "confirmed"
    confirmed_at: Optional[str] = None


class MobileProfileEmploymentSection(BaseModel):
    employment_status: Optional[str] = None
    job_title: Optional[str] = None
    work_sector: Optional[str] = None
    employer_name: Optional[str] = None


class MobileProfileFinancialSection(BaseModel):
    annual_income_range: Optional[str] = None
    net_worth_range: Optional[str] = None
    source_of_wealth: Optional[str] = None


class MobileProfileLegalSection(BaseModel):
    terms_accepted: Optional[str] = None
    info_true_and_accurate: Optional[str] = None
    compliance_usage_ack: Optional[str] = None
    not_us_person: Optional[str] = None


class ActivationJourneyStagePayload(BaseModel):
    """Étape activation — états UX, pondération, CTA (source serveur)."""

    key: str
    id: str
    status: str  # locked | available | in_progress | completed
    weight: float
    is_next_step: bool = False
    title: str
    subtitle: str
    cta_label: str
    target_route: str


class ActivationJourneyPayload(BaseModel):
    config_version: int = 3
    show_module: bool
    activation_complete: bool = False
    completion_message: Optional[str] = None
    weighted_progress_percent: int = 0
    headline: str = ""
    hero_subtitle: str = ""
    remaining_steps_message: str = ""
    primary_cta_label: Optional[str] = None
    primary_cta_target_route: Optional[str] = None
    stages: List[ActivationJourneyStagePayload] = Field(default_factory=list)


class BiometricSecurityStateRead(BaseModel):
    """Lecture structurée V1 — biométrie (UX / préférence, pas preuve de sécurité forte)."""

    preference_enabled: Optional[bool] = None
    preference_updated_at: Optional[datetime] = None
    onboarding_status: Literal["not_started", "completed"] = "not_started"
    onboarding_outcome: Literal["enabled", "skipped", "unavailable", "unknown"] = "unknown"
    onboarding_completed_at: Optional[datetime] = None
    last_client_reported_at: Optional[datetime] = None
    onboarding_source: Literal["app_ios", "app_android", "web", "admin", "unknown"] = "unknown"
    device_capability_last_known: Literal[
        "available", "unavailable", "not_enrolled", "locked_out", "unknown"
    ] = "unknown"


class PushNotificationsSecurityStateRead(BaseModel):
    """Lecture structurée V1 — notifications push."""

    preference_enabled: Optional[bool] = None
    preference_updated_at: Optional[datetime] = None
    onboarding_status: Literal["not_started", "completed"] = "not_started"
    onboarding_outcome: Literal["enabled", "skipped", "unknown"] = "unknown"
    onboarding_completed_at: Optional[datetime] = None
    last_client_reported_at: Optional[datetime] = None
    onboarding_source: Literal["app_ios", "app_android", "web", "admin", "unknown"] = "unknown"
    os_permission_last_known: Literal[
        "unknown", "granted", "denied", "provisional", "limited"
    ] = "unknown"


class MobileSecurityPreferencesRead(BaseModel):
    """Réponse GET/PATCH : modèle structuré V1 + champs legacy plats (projection dérivée)."""

    security_model_version: int = 1
    biometric: BiometricSecurityStateRead
    push_notifications: PushNotificationsSecurityStateRead
    biometric_unlock_enabled: bool = False
    biometric_login_onboarding_completed: bool = False
    push_notifications_enabled: bool = False
    push_notifications_onboarding_completed: bool = False


# Alias historique pour imports existants
MobileSecurityPreferencesSection = MobileSecurityPreferencesRead


class BiometricSecurityPatchIn(BaseModel):
    """PATCH client : champs structurés uniquement (pas de booléens legacy)."""

    model_config = ConfigDict(extra="forbid")

    preference_enabled: Optional[bool] = None
    onboarding_outcome: Optional[
        Literal["enabled", "skipped", "unavailable", "unknown"]
    ] = None
    last_client_reported_at: Optional[datetime] = None
    onboarding_source: Optional[
        Literal["app_ios", "app_android", "web", "admin", "unknown"]
    ] = None
    device_capability_last_known: Optional[
        Literal["available", "unavailable", "not_enrolled", "locked_out", "unknown"]
    ] = None


class PushNotificationsSecurityPatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preference_enabled: Optional[bool] = None
    onboarding_outcome: Optional[Literal["enabled", "skipped", "unknown"]] = None
    last_client_reported_at: Optional[datetime] = None
    onboarding_source: Optional[
        Literal["app_ios", "app_android", "web", "admin", "unknown"]
    ] = None
    os_permission_last_known: Optional[
        Literal["unknown", "granted", "denied", "provisional", "limited"]
    ] = None


class SecurityPreferencesStructuredPatch(BaseModel):
    """PATCH partiel V1 : uniquement ``biometric`` et/ou ``push_notifications`` structurés."""

    model_config = ConfigDict(extra="forbid")

    biometric: Optional[BiometricSecurityPatchIn] = None
    push_notifications: Optional[PushNotificationsSecurityPatchIn] = None

    @model_validator(mode="after")
    def _at_least_one_domain(self) -> "SecurityPreferencesStructuredPatch":
        d = self.model_dump(exclude_unset=True)
        if not d:
            raise ValueError(
                "Au moins une section structurée (biometric ou push_notifications) est requise."
            )
        return self


class MobileAppProfileResponse(BaseModel):
    initials: str
    email: str
    personal: Optional[MobileProfilePersonalSection] = None
    address: Optional[MobileProfileAddressSection] = None
    identity: Optional[MobileProfileIdentitySection] = None
    contact: Optional[MobileProfileContactSection] = None
    employment: Optional[MobileProfileEmploymentSection] = None
    financial: Optional[MobileProfileFinancialSection] = None
    legal: Optional[MobileProfileLegalSection] = None
    jurisdiction: Optional[str] = None
    kyc_status: Optional[str] = None
    client_status: Optional[str] = None
    reference_currency: Optional[str] = None
    # Progression inscription (canonical backend — même source que l’admin)
    registration_completion_ratio: Optional[float] = None
    registration_macro_stage: Optional[str] = None
    registration_macro_label: Optional[str] = None
    registration_missing_steps: Optional[List[str]] = None
    registration_completed_steps: Optional[List[str]] = None
    registration_session_progress_percent: Optional[int] = None
    registration_session_current_step_key: Optional[str] = None
    registration_session_current_screen_key: Optional[str] = None
    # Progression dérivée uniquement de profile_json.collected (jalons canoniques)
    registration_derived_completion_ratio: Optional[float] = None
    registration_derived_progress_percent: Optional[int] = None
    registration_derived_next_step_key: Optional[str] = None
    registration_derived_next_step_label: Optional[str] = None
    registration_derived_resume_description: Optional[str] = None
    registration_derived_completed_count: Optional[int] = None
    registration_derived_total_count: Optional[int] = None
    activation_journey: Optional[ActivationJourneyPayload] = None
    security_preferences: Optional[MobileSecurityPreferencesRead] = None
    contact_email_change: Optional[MobileContactEmailChangeSection] = None


# ---------------------------------------------------------------------------
# Cash endpoint
# ---------------------------------------------------------------------------

CURRENCY_SYMBOLS: dict[str, str] = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "CHF": "CHF",
    "AED": "AED",
}


class CashAccountPayload(BaseModel):
    account_id: UUID
    iban: Optional[str] = None
    currency: str
    currency_symbol: str = "€"
    available_balance: str
    pending_balance: str


class CashTransactionPayload(BaseModel):
    id: UUID
    type: str
    transaction_kind: Optional[str] = None
    direction: str
    amount: str
    currency: str
    status: str
    external_reference: Optional[str] = None
    provider: Optional[str] = None
    remitter_name: Optional[str] = None
    narrative: Optional[str] = None
    created_at: datetime


class CashResponse(BaseModel):
    client: BootstrapClientPayload
    cash_account: Optional[CashAccountPayload] = None
    recent_transactions: list[CashTransactionPayload] = []
    last_updated: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Transaction detail endpoint
# ---------------------------------------------------------------------------

TRANSACTION_TITLE_MAP: dict[str, str] = {
    "deposit": "Virement entrant",
    "withdrawal": "Retrait",
    "transfer_internal": "Transfert interne",
}

TRANSACTION_KIND_TITLE_MAP: dict[str, str] = {
    "bank_transfer_in": "Virement entrant",
    "bank_transfer_out": "Virement sortant",
    "internal_transfer": "Transfert interne",
    "exchange_buy": "Achat",
    "exchange_sell": "Vente",
}

STATUS_LABEL_MAP: dict[str, str] = {
    "completed": "Complété",
    "pending": "En cours",
    "failed": "Échoué",
    "reversed": "Annulé",
    "processing": "En traitement",
}


class TransactionDetailResponse(BaseModel):
    id: UUID
    transaction_type: str
    transaction_kind: Optional[str] = None
    direction: str
    amount: str
    currency: str
    currency_symbol: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    title: str
    status_label: str

    source_system: Optional[str] = Field(
        default=None,
        description="Système source de l'opération : custody | exchange",
    )
    source_id: Optional[str] = Field(
        default=None,
        description="Identifiant stable dans le système source (UUID)",
    )

    external_reference: Optional[str] = None
    provider_reference: Optional[str] = None
    provider_name: Optional[str] = None

    remitter_name: Optional[str] = None
    remitter_iban: Optional[str] = None
    remitter_bank_name: Optional[str] = None

    account_holder_name: Optional[str] = None
    target_iban: Optional[str] = None

    booking_date: Optional[str] = None
    value_date: Optional[str] = None

    narrative: Optional[str] = None


# ---------------------------------------------------------------------------
# Euro Account endpoint
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Crypto Positions endpoint
# ---------------------------------------------------------------------------

ASSET_NAMES: dict[str, str] = {
    "BTC": "Bitcoin",
    "CBBTC": "Bitcoin",
    "ETH": "Ethereum",
    "CBETH": "Ethereum",
    "USDC": "USD Coin",
    "EURC": "Euro Coin",
    "LINK": "Chainlink",
    "AAVE": "Aave",
    "UNI": "Uniswap",
    "SOL": "Solana",
    "XRP": "Ripple",
    "ADA": "Cardano",
}


class CryptoPositionPayload(BaseModel):
    asset: str
    name: str
    balance: str
    available_balance: str
    price_eur: Optional[str] = None
    estimated_value_eur: Optional[str] = None
    price_usd: Optional[str] = None
    estimated_value_usd: Optional[str] = None
    performance_1d_pct: Optional[str] = None
    icon_key: str
    portfolio_scope: Optional[str] = None
    privy_balance: Optional[str] = None
    platform_balance: Optional[str] = None
    dedicated_wallet: Optional[bool] = None
    chain_type: Optional[str] = None
    chain_id: Optional[int] = None
    wallet_address: Optional[str] = None
    swappable_balance: Optional[str] = None


class PortfolioBreakdownComponentMeta(BaseModel):
    economic_scope: str
    ownership_scope: str
    additive: bool
    quantity: str
    bundle_is_subset_of_wallet: Optional[bool] = None
    in_bundles_additive: Optional[bool] = None


class PortfolioBreakdownAssetPayload(BaseModel):
    symbol: str
    total_holdings: str
    available: str
    in_vaults: str
    in_bundles: str
    locked_collateral: str
    debt: str
    pending_settlement: str
    swappable_balance: str
    wallet_ledger_balance: str
    on_chain_balance_base: str
    bundle_incremental_value: str
    bundle_is_subset_of_wallet: bool
    in_bundles_additive: bool
    non_additive_overlap: str
    components: dict[str, PortfolioBreakdownComponentMeta]


class PortfolioBreakdownDoctrine(BaseModel):
    hierarchy: list[str]
    operational_source_of_truth: list[str]
    total_holdings_formula: str
    total_holdings_note: str
    swappable_formula: str
    swap_max_field: str


class PortfolioBreakdownResponse(BaseModel):
    breakdown_version: str
    person_id: str
    doctrine: PortfolioBreakdownDoctrine
    warnings: list[str]
    non_additive_components: list[str]
    assets: list[PortfolioBreakdownAssetPayload]


class CryptoPositionsSummary(BaseModel):
    total_value_eur: str
    total_value_usd: Optional[str] = None
    positions_count: int
    direct_positions_count: Optional[int] = None
    bundles_count: Optional[int] = None


class CryptoPositionsResponse(BaseModel):
    client: BootstrapClientPayload
    summary: CryptoPositionsSummary
    positions: list[CryptoPositionPayload] = []


class CryptoWalletDetailPayload(BaseModel):
    asset: str
    name: str
    icon_key: str
    volume: str
    current_price_eur: Optional[str] = None
    current_price_usd: Optional[str] = None
    total_value_eur: str
    total_value_usd: Optional[str] = None
    avg_buy_price_eur: Optional[str] = None
    avg_buy_price_usd: Optional[str] = None
    average_purchase_price: Optional[str] = None
    cost_basis: Optional[str] = None
    unrealized_gain_eur: Optional[str] = None
    unrealized_gain_usd: Optional[str] = None
    unrealized_gains: Optional[str] = None
    unrealized_gains_pct: Optional[str] = None
    realized_gain_eur: str = "0.00"
    realized_gain_usd: str = "0.00"
    realized_gains: str = "0.00"
    total_gain_eur: Optional[str] = None
    total_gain_usd: Optional[str] = None
    total_gains: Optional[str] = None
    total_gains_pct: Optional[str] = None
    portfolio_scope: Optional[str] = None
    privy_balance: Optional[str] = None
    platform_balance: Optional[str] = None


class CryptoWalletDetailResponse(BaseModel):
    client: BootstrapClientPayload
    detail: Optional[CryptoWalletDetailPayload] = None


class CryptoTransactionPayload(BaseModel):
    id: UUID
    side: str
    asset: str
    amount_crypto: str
    amount_fiat: str
    price: str
    currency: str
    status: str
    fee_amount: Optional[str] = None
    fee_asset: Optional[str] = None
    external_reference: Optional[str] = None
    created_at: datetime
    title: str
    subtitle: str
    direction: str
    from_asset: Optional[str] = None
    to_asset: Optional[str] = None
    swap_amount_from: Optional[str] = None
    swap_amount_to: Optional[str] = None
    transaction_kind: Optional[str] = None
    source_system: Optional[str] = None
    tx_hash: Optional[str] = None
    custody_provider: Optional[str] = None


class CryptoTransactionsResponse(BaseModel):
    client: BootstrapClientPayload
    asset: str
    transactions: list[CryptoTransactionPayload] = []


# ---------------------------------------------------------------------------
# Euro Account endpoint
# ---------------------------------------------------------------------------


class EuroAccountPayload(BaseModel):
    account_id: UUID
    currency: str = "EUR"
    currency_symbol: str = "€"
    balance: str
    pending_balance: str
    iban_masked: Optional[str] = None
    account_holder_name: Optional[str] = None


class EuroTransactionPayload(BaseModel):
    id: UUID
    transaction_kind: Optional[str] = None
    transaction_type: str
    direction: str
    amount: str
    currency: str
    currency_symbol: str = "€"
    status: str
    title: str
    subtitle: str
    created_at: datetime
    external_reference: Optional[str] = None
    provider: Optional[str] = None
    remitter_name: Optional[str] = None
    narrative: Optional[str] = None


class EuroAccountResponse(BaseModel):
    client: BootstrapClientPayload
    account: Optional[EuroAccountPayload] = None
    transactions: list[EuroTransactionPayload] = []


# ---------------------------------------------------------------------------
# IBAN Details endpoint
# ---------------------------------------------------------------------------


class IbanDetailsPayload(BaseModel):
    account_holder_name: str
    iban: Optional[str] = None
    bic: Optional[str] = None
    currency: str = "EUR"
    currency_symbol: str = "€"


class IbanDetailsResponse(BaseModel):
    client: BootstrapClientPayload
    iban_details: Optional[IbanDetailsPayload] = None
