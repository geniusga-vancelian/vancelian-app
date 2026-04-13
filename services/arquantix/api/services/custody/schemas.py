"""Pydantic schemas for the Custody module."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import (
    CustodyAccountStatus,
    CustodyAccountType,
    ProviderStatus,
    ProviderType,
    TransactionDirection,
    TransactionStatus,
    TransactionType,
)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class ProviderCreate(BaseModel):
    name: str = Field(..., max_length=100)
    provider_type: ProviderType
    jurisdiction: Optional[str] = Field(None, max_length=50)
    api_base_url: Optional[str] = Field(None, max_length=500)
    status: ProviderStatus = ProviderStatus.ACTIVE
    metadata: Optional[dict[str, Any]] = None


class ProviderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    provider_type: str
    jurisdiction: Optional[str] = None
    api_base_url: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class ProviderListResponse(BaseModel):
    items: list[ProviderRead]
    total: int


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

class AccountCreate(BaseModel):
    provider_id: UUID
    account_type: CustodyAccountType
    currency: str = Field("EUR", max_length=10)
    iban: Optional[str] = Field(None, max_length=50)
    bic: Optional[str] = Field(None, max_length=20)
    account_holder_name: str = Field(..., max_length=255)
    client_id: Optional[UUID] = None
    is_master_account: bool = False
    metadata: Optional[dict[str, Any]] = None


class CanonicalClientAccountCreate(BaseModel):
    """Création custody client dépôt avec résolution stricte Person → pe_client (recommandé)."""

    provider_id: UUID
    currency: str = Field("EUR", max_length=10)
    iban: Optional[str] = Field(None, max_length=50)
    bic: Optional[str] = Field(None, max_length=20)
    account_holder_name: str = Field(..., max_length=255)
    person_id: Optional[UUID] = None
    phone_e164: Optional[str] = None
    pe_client_id: Optional[UUID] = None

    @model_validator(mode="after")
    def _exactly_one_resolution_field(self) -> CanonicalClientAccountCreate:
        has_p = self.person_id is not None
        has_tel = bool((self.phone_e164 or "").strip())
        has_c = self.pe_client_id is not None
        if int(has_p) + int(has_tel) + int(has_c) != 1:
            raise ValueError(
                "Fournir exactement un des champs : person_id, phone_e164 ou pe_client_id."
            )
        return self


class CustodyIdentityResolveRequest(BaseModel):
    """Prévisualisation résolution identité (sans création de compte)."""

    person_id: Optional[UUID] = None
    phone_e164: Optional[str] = None
    pe_client_id: Optional[UUID] = None

    @model_validator(mode="after")
    def _exactly_one_resolution_field(self) -> CustodyIdentityResolveRequest:
        has_p = self.person_id is not None
        has_tel = bool((self.phone_e164 or "").strip())
        has_c = self.pe_client_id is not None
        if int(has_p) + int(has_tel) + int(has_c) != 1:
            raise ValueError(
                "Fournir exactement un des champs : person_id, phone_e164 ou pe_client_id."
            )
        return self


class CustodyIdentityResolveResponse(BaseModel):
    person_id: UUID
    pe_client_id: UUID
    person_email_collected: Optional[str] = None
    pe_client_email: Optional[str] = None
    phone_e164: Optional[str] = None
    resolution_source: str


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_id: UUID
    account_type: str
    currency: str
    iban: Optional[str] = None
    bic: Optional[str] = None
    account_holder_name: str
    client_id: Optional[UUID] = None
    ledger_account_id: Optional[UUID] = None
    is_master_account: bool
    status: str
    created_at: datetime
    updated_at: datetime
    available_balance: Optional[Decimal] = None
    pending_balance: Optional[Decimal] = None
    provider_name: Optional[str] = None
    client_email: Optional[str] = None
    person_id: Optional[UUID] = None
    person_email_collected: Optional[str] = None
    phone_e164: Optional[str] = None


class AccountListResponse(BaseModel):
    items: list[AccountRead]
    total: int


class SimpleEuroAccountCreateRequest(BaseModel):
    """Création euro (EUR) minimaliste : uniquement ``person_id`` — le reste est dérivé côté serveur."""

    person_id: UUID


class SimpleEuroAccountCreateResponse(BaseModel):
    """Réponse création simplifiée (ops / tests)."""

    message: str = "Euro deposit account created successfully."
    account: AccountRead


class DepositSimulationClientItem(BaseModel):
    """Customer (Portfolio Engine client) avec compte dépôt custody dans la devise — simulateur webhook BAS."""

    client_id: UUID
    email: str
    iban: Optional[str] = None
    account_holder_name: str
    available_balance: Optional[Decimal] = None
    label: str = Field(..., description="Libellé ops : titulaire + e-mail")


class DepositSimulationClientsResponse(BaseModel):
    items: list[DepositSimulationClientItem]


# ---------------------------------------------------------------------------
# Balances
# ---------------------------------------------------------------------------

class BalanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    available_balance: Decimal
    pending_balance: Decimal
    currency: str
    version: int
    last_updated_at: datetime


class BalanceListResponse(BaseModel):
    items: list[BalanceRead]
    total: int


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    provider_id: Optional[UUID] = None
    transaction_type: str
    transaction_kind: Optional[str] = None
    direction: str
    amount: Decimal
    currency: str
    status: str
    external_reference: Optional[str] = None
    provider_reference: Optional[str] = None
    failure_reason: Optional[str] = None
    reversal_of_transaction_id: Optional[UUID] = None
    metadata_: Optional[dict[str, Any]] = None
    client_email: Optional[str] = None
    provider_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class TransactionListResponse(BaseModel):
    items: list[TransactionRead]
    total: int


# ---------------------------------------------------------------------------
# Webhook Events
# ---------------------------------------------------------------------------

class WebhookEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_id: UUID
    event_type: str
    external_reference: Optional[str] = None
    payload_hash: str
    processing_status: str
    error_message: Optional[str] = None
    linked_transaction_id: Optional[UUID] = None
    retry_count: int
    received_at: datetime
    processed_at: Optional[datetime] = None


class WebhookEventListResponse(BaseModel):
    items: list[WebhookEventRead]
    total: int


# ---------------------------------------------------------------------------
# Simulation payloads
# ---------------------------------------------------------------------------

class SimulateDepositRequest(BaseModel):
    client_id: UUID
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("EUR", max_length=10)
    reference: Optional[str] = Field(None, max_length=255)


class SimulateWithdrawalRequest(BaseModel):
    client_id: UUID
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("EUR", max_length=10)
    reference: Optional[str] = Field(None, max_length=255)


class SimulateResponse(BaseModel):
    transaction_id: UUID
    account_id: UUID
    direction: str
    amount: Decimal
    new_available_balance: Decimal
    message: str


# ---------------------------------------------------------------------------
# Internal Transfer
# ---------------------------------------------------------------------------

class InternalTransferRequest(BaseModel):
    client_account_id: UUID
    settlement_account_id: UUID
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("EUR", max_length=10)
    external_reference: str = Field(..., min_length=1, max_length=255)


class InternalTransferResponse(BaseModel):
    status: str
    transaction_id: Optional[UUID] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    client_balance_after: Optional[Decimal] = None
    settlement_balance_after: Optional[Decimal] = None
    error: Optional[str] = None
    reason: Optional[str] = None
