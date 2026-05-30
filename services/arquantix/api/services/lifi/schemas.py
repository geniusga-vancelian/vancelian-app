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


class SwapSubmitRequest(BaseModel):
    tx_hash: str = Field(..., min_length=8, max_length=120)


class SwapApprovalSubmitRequest(BaseModel):
    tx_hash: str = Field(..., min_length=8, max_length=120)


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


class SwapSupportedAssetsResponse(BaseModel):
    assets: list[dict[str, Any]]
    source_assets: list[dict[str, Any]]
    destination_assets: list[dict[str, Any]]
    chains: list[dict[str, Any]]
    swap_fee_bps: int
    default_slippage_bps: int
    max_slippage_bps: int
    mock_mode: bool = False
