"""Schémas Pydantic — swap LI.FI orchestré par Vancelian."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class SwapQuoteRequest(BaseModel):
    from_asset: str = Field(..., min_length=1, max_length=20)
    to_asset: str = Field(..., min_length=1, max_length=20)
    amount: str = Field(..., min_length=1, max_length=64, description="Montant humain (ex. 1000)")
    from_chain: str = Field(..., min_length=1, max_length=32)
    to_chain: str = Field(..., min_length=1, max_length=32)
    slippage_bps: Optional[int] = Field(None, ge=1, le=100)
    signing_wallet_mode: str = Field(
        default="privy_embedded",
        description="privy_embedded | external_evm",
    )
    signing_wallet_address: Optional[str] = Field(
        None,
        max_length=80,
        description="Adresse EVM requise si signing_wallet_mode=external_evm",
    )


class SwapRouteStep(BaseModel):
    label: str
    kind: str
    chain: str


class SwapQuoteResponse(BaseModel):
    swap_id: UUID
    status: str
    from_asset: str
    to_asset: str
    from_chain: str
    to_chain: str
    amount_in: str
    vancelian_fee: str
    vancelian_fee_bps: int
    network_fee: str
    network_fee_asset: Optional[str] = None
    network_fee_usd: Optional[str] = None
    estimated_receive: str
    estimated_receive_min: str
    exchange_rate: Optional[str] = None
    estimated_duration_seconds: Optional[int] = None
    route_steps: list[SwapRouteStep] = Field(default_factory=list)
    expires_at: str
    slippage_bps: int
    signing_wallet_mode: Optional[str] = None
    signing_wallet_address: Optional[str] = None


class SwapConfirmExecuteRequest(BaseModel):
    swap_id: UUID
    review_estimated_receive: str = Field(..., min_length=1, max_length=64)
    review_amount_in: Optional[str] = Field(None, max_length=64)


class SwapExecuteRequest(BaseModel):
    swap_id: UUID


class SwapTransactionPayload(BaseModel):
    chain_id: Union[int, str]
    to: str
    data: str
    value: str
    gas_limit: Optional[str] = None
    gas_price: Optional[str] = None


class SwapTokenApprovalPayload(BaseModel):
    required: bool = False
    token_address: Optional[str] = None
    spender_address: Optional[str] = None
    amount_atomic: Optional[str] = None


class SwapExecuteResponse(BaseModel):
    swap_id: UUID
    status: str
    lifecycle_message: str
    transaction: Optional[SwapTransactionPayload] = None
    lifi_tool: Optional[str] = None
    signing_wallet_mode: Optional[str] = None
    signing_wallet_address: Optional[str] = None
    token_approval: Optional[SwapTokenApprovalPayload] = None


class SwapConfirmExecuteResponse(BaseModel):
    freshness: str = Field(..., description="verified | refreshed")
    quote: SwapQuoteResponse
    execute: SwapExecuteResponse


class SwapPriceChangedDetail(BaseModel):
    code: str = "swap.price_changed"
    message: str
    quote: SwapQuoteResponse
    delta_bps: int
    slippage_bps: int


class SwapSubmitRequest(BaseModel):
    tx_hash: str = Field(..., min_length=8, max_length=120)
    signing_wallet_address: Optional[str] = Field(
        None,
        max_length=80,
        description="Adresse wallet connectée — vérification cohérence avec le devis verrouillé",
    )


class SwapApprovalSubmitRequest(BaseModel):
    tx_hash: str = Field(..., min_length=8, max_length=120)
    signing_wallet_address: Optional[str] = Field(
        None,
        max_length=80,
        description="Adresse wallet connectée — vérification cohérence avec le devis verrouillé",
    )


class SwapFailureRecordRequest(BaseModel):
    failure_phase: str = Field(..., min_length=1, max_length=32)
    error_code: str = Field(..., min_length=1, max_length=64)
    technical_message: Optional[str] = Field(None, max_length=2000)
    signing_wallet_address: Optional[str] = Field(None, max_length=80)


class SwapClientTraceRequest(BaseModel):
    step: str = Field(..., min_length=1, max_length=64)
    phase: Optional[str] = Field(None, max_length=32)
    detail: Optional[str] = Field(None, max_length=500)
    correlation_id: Optional[str] = Field(None, max_length=128)


class SwapAbandonRequest(BaseModel):
    explicit_user_abandon: bool = Field(
        default=False,
        description="True uniquement si l'utilisateur ferme volontairement le flux",
    )
    failure_phase: Optional[str] = Field(
        None,
        max_length=32,
        description="Phase au moment de l'abandon explicite (approval, signing, etc.)",
    )
    reason: Optional[str] = Field(None, max_length=500)


class SwapStatusResponse(BaseModel):
    swap_id: UUID
    status: str
    lifecycle_message: str
    from_asset: str
    to_asset: str
    from_chain: str
    to_chain: str
    amount_in: str
    estimated_receive: Optional[str] = None
    tx_hash: Optional[str] = None
    error_message: Optional[str] = None


class SwapServerExecuteResponse(BaseModel):
    """Résultat d'une exécution serveur (signature déléguée Privy, sans navigateur)."""

    swap_id: UUID
    phase: str  # confirmed | submitted | awaiting_signature | failed | expired
    signed_server_side: bool
    settled: bool = False
    tx_hash: Optional[str] = None
    fallback_reason: Optional[str] = None


class SwapSupportedAssetsResponse(BaseModel):
    assets: list[dict[str, Any]]
    source_assets: list[dict[str, Any]]
    destination_assets: list[dict[str, Any]]
    chains: list[dict[str, Any]]
    swap_fee_bps: int
    default_slippage_bps: int
    max_slippage_bps: int
    mock_mode: bool = False
