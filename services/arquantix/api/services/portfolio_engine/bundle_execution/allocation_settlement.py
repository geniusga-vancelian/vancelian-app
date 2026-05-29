"""Montants réels post-confirmation pour settlement PE bundle (Phase 5A)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from config.supported_swap_assets import atomic_amount_to_human
from services.lifi.lifi_actual_receive import (
    LifiActualReceiveResult,
    resolve_lifi_actual_receive_amount,
)


@dataclass(frozen=True)
class BundleLegSettlementAmounts:
    amount_in: Decimal
    amount_out: Decimal
    planned_amount_in: Decimal
    planned_amount_out: Decimal
    amount_in_source: str
    amount_out_source: str


def _asset_decimals(asset: str) -> int:
    from config.supported_swap_assets import SUPPORTED_SWAP_ASSETS

    meta = SUPPORTED_SWAP_ASSETS.get(str(asset).upper(), {})
    return int(meta.get("decimals") or 18)


def _amount_from_lifi_sending_payload(
    lifi_status_payload: dict[str, Any] | None,
    *,
    from_asset: str,
) -> Decimal | None:
    if not lifi_status_payload:
        return None
    sending = lifi_status_payload.get("sending")
    if not isinstance(sending, dict):
        return None
    amount_atomic = sending.get("amount")
    if amount_atomic is None or str(amount_atomic).strip() in {"", "0"}:
        return None
    token = sending.get("token") if isinstance(sending.get("token"), dict) else {}
    token_symbol = str(token.get("symbol") or "").strip().upper()
    asset_u = from_asset.upper()
    if token_symbol and token_symbol != asset_u:
        return None
    decimals = int(token.get("decimals") or _asset_decimals(asset_u))
    amount = atomic_amount_to_human(str(amount_atomic), decimals)
    return amount if amount > 0 else None


def _actual_amount_in_from_audit(swap) -> Decimal | None:
    for entry in reversed(swap.audit_log or []):
        if not isinstance(entry, dict):
            continue
        if entry.get("actual_amount_in") is not None:
            val = Decimal(str(entry["actual_amount_in"]))
            return val if val > 0 else None
        if entry.get("event") == "swap_settled" and entry.get("actual_amount_in") is not None:
            val = Decimal(str(entry["actual_amount_in"]))
            return val if val > 0 else None
    return None


def _actual_receive_from_audit(swap) -> Decimal | None:
    for entry in reversed(swap.audit_log or []):
        if not isinstance(entry, dict):
            continue
        if entry.get("actual_receive_amount") is not None:
            val = Decimal(str(entry["actual_receive_amount"]))
            return val if val > 0 else None
        if entry.get("event") == "swap_settled" and entry.get("actual_receive_amount") is not None:
            val = Decimal(str(entry["actual_receive_amount"]))
            return val if val > 0 else None
    return None


def resolve_allocation_leg_settlement_amounts(
    db: Session,
    swap,
    *,
    planned_amount_in: Decimal | None = None,
    lifi_status_payload: dict[str, Any] | None = None,
    allow_mock_quote_amount: bool = False,
) -> BundleLegSettlementAmounts:
    """Résout montants réels PE — fallback quote si réel indisponible."""
    quoted_in = Decimal(str(swap.amount_in))
    quoted_out = Decimal(str(swap.estimated_receive or 0))
    planned_in = planned_amount_in if planned_amount_in is not None else quoted_in

    amount_in = _actual_amount_in_from_audit(swap)
    amount_in_source = "audit_actual_amount_in"
    if amount_in is None:
        from_sending = _amount_from_lifi_sending_payload(
            lifi_status_payload, from_asset=str(swap.from_asset),
        )
        if from_sending is not None:
            amount_in = from_sending
            amount_in_source = "lifi_status_sending"
    if amount_in is None:
        amount_in = quoted_in
        amount_in_source = "quoted_amount_in"

    actual_receive: LifiActualReceiveResult | None = None
    audited_out = _actual_receive_from_audit(swap)
    if audited_out is not None:
        amount_out = audited_out
        amount_out_source = "audit_actual_receive"
    else:
        actual_receive = resolve_lifi_actual_receive_amount(
            db,
            swap,
            lifi_status_payload=lifi_status_payload,
            allow_mock_quote_amount=allow_mock_quote_amount,
        )
        if actual_receive is not None and actual_receive.amount > 0:
            amount_out = actual_receive.amount
            amount_out_source = actual_receive.source
        elif quoted_out > 0:
            amount_out = quoted_out
            amount_out_source = "quoted_estimated_receive"
        else:
            amount_out = Decimal("0")
            amount_out_source = "missing"

    return BundleLegSettlementAmounts(
        amount_in=amount_in,
        amount_out=amount_out,
        planned_amount_in=planned_in,
        planned_amount_out=quoted_out,
        amount_in_source=amount_in_source,
        amount_out_source=amount_out_source,
    )
