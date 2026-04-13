"""Pydantic schemas for the Exchange module."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ExchangeBuyRequest(BaseModel):
    client_id: UUID
    asset: str = Field(..., min_length=1, max_length=20)
    fiat_amount: Decimal = Field(..., gt=0)
    currency: str = Field("EUR", max_length=10)
    external_reference: str = Field(..., min_length=1, max_length=255)
    price: Optional[Decimal] = Field(None, gt=0, description="Override price per unit (for testing / locked quotes)")


class ExchangeBuyResponse(BaseModel):
    status: str
    order_id: Optional[UUID] = None
    asset: Optional[str] = None
    from_asset: Optional[str] = None
    to_asset: Optional[str] = None
    amount_from: Optional[Decimal] = None
    amount_to: Optional[Decimal] = None
    amount_crypto: Optional[Decimal] = None
    amount_fiat: Optional[Decimal] = None
    volume_raw: Optional[Decimal] = None
    fee_amount: Optional[Decimal] = None
    fee_asset: Optional[str] = None
    fee_bps: Optional[int] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    client_eur_balance_after: Optional[Decimal] = None
    crypto_position_after: Optional[Decimal] = None
    error: Optional[str] = None
    reason: Optional[str] = None


class ExchangeSellRequest(BaseModel):
    client_id: UUID
    asset: str = Field(..., min_length=1, max_length=20)
    amount_crypto: Decimal = Field(..., gt=0)
    currency: str = Field("EUR", max_length=10)
    external_reference: str = Field(..., min_length=1, max_length=255)
    price: Optional[Decimal] = Field(None, gt=0, description="Override price per unit (for testing / locked quotes)")


class ExchangeSellResponse(BaseModel):
    status: str
    order_id: Optional[UUID] = None
    asset: Optional[str] = None
    from_asset: Optional[str] = None
    to_asset: Optional[str] = None
    amount_from: Optional[Decimal] = None
    amount_to: Optional[Decimal] = None
    amount_crypto: Optional[Decimal] = None
    price_eur: Optional[Decimal] = None
    gross_eur: Optional[Decimal] = None
    fee_eur: Optional[Decimal] = None
    fee_bps: Optional[int] = None
    net_eur: Optional[Decimal] = None
    currency: Optional[str] = None
    client_eur_balance_after: Optional[Decimal] = None
    crypto_position_after: Optional[Decimal] = None
    cost_basis_consumed: Optional[str] = None
    realized_pnl_generated: Optional[str] = None
    error: Optional[str] = None
    reason: Optional[str] = None


class CryptoPositionRead(BaseModel):
    id: UUID
    client_id: UUID
    asset: str
    balance: Decimal
    available_balance: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExchangeOrderRead(BaseModel):
    id: UUID
    client_id: UUID
    side: str
    asset: str
    amount_crypto: Decimal
    amount_fiat: Decimal
    price: Decimal
    currency: str
    from_asset: Optional[str] = None
    to_asset: Optional[str] = None
    amount_from: Optional[Decimal] = None
    amount_to: Optional[Decimal] = None
    fee_amount: Optional[Decimal] = None
    fee_asset: Optional[str] = None
    status: str
    external_reference: str
    failure_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SettlementRunResponse(BaseModel):
    settled_count: int
    blocked_count: int = 0
    details: list[dict]


# ---------------------------------------------------------------------------
# Swap crypto ↔ crypto
# ---------------------------------------------------------------------------

class SwapPreviewRequest(BaseModel):
    from_asset: str = Field(..., min_length=1, max_length=20)
    to_asset: str = Field(..., min_length=1, max_length=20)
    amount_from: Decimal = Field(..., gt=0)


class SwapPreviewResponse(BaseModel):
    from_asset: str
    to_asset: str
    amount_from: Decimal
    estimated_reference_value_gross: float
    fee_in_reference_currency: float
    estimated_reference_value_net: float
    estimated_to_amount: float
    from_price_in_ref_ccy: float
    to_price_in_ref_ccy: float
    reference_currency: str
    is_fresh: bool


class SwapRequest(BaseModel):
    from_asset: str = Field(..., min_length=1, max_length=20)
    to_asset: str = Field(..., min_length=1, max_length=20)
    amount_from: Decimal = Field(..., gt=0)
    external_reference: Optional[str] = Field(None, min_length=1, max_length=255)


class SwapResponse(BaseModel):
    status: str
    swap_group_id: Optional[UUID] = None
    sell_order_id: Optional[UUID] = None
    buy_order_id: Optional[UUID] = None
    from_asset: Optional[str] = None
    to_asset: Optional[str] = None
    amount_from: Optional[Decimal] = None
    amount_to: Optional[Decimal] = None
    reference_value_gross: Optional[float] = None
    fee_in_reference_currency: Optional[float] = None
    reference_value_net: Optional[float] = None
    cost_basis_consumed: Optional[str] = None
    realized_pnl_generated: Optional[str] = None
    from_position_after: Optional[Decimal] = None
    to_position_after: Optional[Decimal] = None
    error: Optional[str] = None
