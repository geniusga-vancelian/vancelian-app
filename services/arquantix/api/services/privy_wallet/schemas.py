"""Pydantic schemas for Privy user-wallet ledger API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PrivyWalletBalancePayload(BaseModel):
    asset: str
    name: str
    balance: str
    available_balance: str
    icon_key: str
    wallet_address: Optional[str] = None
    chain_type: Optional[str] = None
    chain_id: Optional[int] = None


class PrivyWalletBalancesSummary(BaseModel):
    positions_count: int
    wallet_count: int


class PrivyWalletBalancesResponse(BaseModel):
    summary: PrivyWalletBalancesSummary
    balances: list[PrivyWalletBalancePayload] = Field(default_factory=list)


class PrivyWalletDepositPayload(BaseModel):
    id: UUID
    transaction_kind: str
    direction: str
    asset: str
    amount: str
    status: str
    chain_type: str
    chain_id: Optional[int] = None
    tx_hash: str
    from_address: Optional[str] = None
    to_address: str
    confirmations: int
    title: str
    subtitle: Optional[str] = None
    wallet_address: Optional[str] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None


class PrivyWalletDepositsResponse(BaseModel):
    asset: Optional[str] = None
    deposits: list[PrivyWalletDepositPayload] = Field(default_factory=list)


class PrivySimulateDepositRequest(BaseModel):
    person_id: UUID
    amount: str = Field(..., description="Montant lisible (ex. 1, 0.5)")
    asset: str = Field("ETH", max_length=20)
    chain_id: Optional[int] = Field(None, description="Défaut : chain_id du wallet actif")
    wallet_address: Optional[str] = Field(
        None,
        description="Adresse cible si plusieurs wallets actifs ; sinon wallet primaire.",
    )


class PrivySimulateDepositResponse(BaseModel):
    event_id: UUID
    deposit_id: Optional[UUID] = None
    processing_status: str
    asset: str
    amount: str
    new_balance: Optional[str] = None
    tx_hash: str
    message: str


class PrivyReconcileWalletsRequest(BaseModel):
    person_id: UUID
    manual_address: Optional[str] = Field(
        None,
        description="Repli si l’API Privy est indisponible — adresse EVM 0x…",
    )
    chain_id: Optional[int] = Field(None, description="Chain EVM pour l’adresse manuelle (défaut 1).")


class PrivyReconcileWalletItem(BaseModel):
    id: str
    address: str
    chain_type: str
    chain_id: Optional[int] = None
    wallet_type: str
    provider: str
    is_primary: bool


class PrivyReconcileWalletsResponse(BaseModel):
    synced_count: int
    wallets: list[PrivyReconcileWalletItem] = Field(default_factory=list)
    source: str
    privy_user_id: Optional[str] = None
    api_error: Optional[str] = None
    message: str


class PrivyInfraReadinessResponse(BaseModel):
    ready_for_live_deposits: bool
    blockers: list[str] = Field(default_factory=list)
    exchange: dict
    webhook: dict
    reconcile_api: dict
    ledger_schema: dict
    notes: list[str] = Field(default_factory=list)


class PrivyCustomerReadinessResponse(BaseModel):
    person_id: str
    email_hint: Optional[str] = None
    privy_user_id: Optional[str] = None
    pe_client_id: Optional[str] = None
    primary_wallet: Optional[dict] = None
    balances_count: int = 0
    recent_deposits_count: int = 0
    checks: list[dict] = Field(default_factory=list)
    infra: dict
    ready_for_live_deposit: bool
    blockers: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
