"""execute_trade — unified LI.FI leg execution with virtual wallet context (ADR 008)."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.swap_repository import PersonWalletSwapRepository
from services.portfolio_engine.bundle_execution.types import ExecutionLeg, ExecutionResult
from services.portfolio_engine.wallets.resolver import portfolio_scope_from_wallet

from .types import TradeExecutionResult, TradeRequest

logger = logging.getLogger(__name__)

WALLET_CONTEXT_EVENT = "trade_wallet_context"


def attach_trade_wallet_context(
    db: Session,
    swap_repo: PersonWalletSwapRepository,
    swap,
    *,
    wallet_from_id: UUID,
    wallet_to_id: UUID,
    correlation_id: UUID,
    instrument_from_id: UUID,
    instrument_to_id: UUID,
) -> None:
    scope_from, pf_from = portfolio_scope_from_wallet(db, wallet_from_id)
    scope_to, pf_to = portfolio_scope_from_wallet(db, wallet_to_id)
    swap_repo.append_audit(
        swap,
        {
            "event": WALLET_CONTEXT_EVENT,
            "wallet_from_id": str(wallet_from_id),
            "wallet_to_id": str(wallet_to_id),
            "correlation_id": str(correlation_id),
            "instrument_from_id": str(instrument_from_id),
            "instrument_to_id": str(instrument_to_id),
            "portfolio_scope_from": scope_from,
            "portfolio_id_from": str(pf_from) if pf_from else None,
            "portfolio_scope_to": scope_to,
            "portfolio_id_to": str(pf_to) if pf_to else None,
        },
    )


def read_trade_wallet_context(swap) -> dict[str, str] | None:
    audit = swap.audit_log
    if not isinstance(audit, list):
        return None
    for entry in reversed(audit):
        if isinstance(entry, dict) and entry.get("event") == WALLET_CONTEXT_EVENT:
            return {
                "wallet_from_id": str(entry.get("wallet_from_id") or ""),
                "wallet_to_id": str(entry.get("wallet_to_id") or ""),
                "correlation_id": str(entry.get("correlation_id") or ""),
                "instrument_from_id": str(entry.get("instrument_from_id") or ""),
                "instrument_to_id": str(entry.get("instrument_to_id") or ""),
            }
    return None


def trade_request_to_execution_leg(request: TradeRequest) -> ExecutionLeg:
    return ExecutionLeg(
        leg_id=request.leg_id,
        portfolio_id=request.portfolio_id,
        client_id=request.client_id,
        action=request.leg_action,  # type: ignore[arg-type]
        from_asset=request.from_asset,
        to_asset=request.to_asset,
        amount_from=request.quantity_from,
        batch_id=request.batch_id,
        bundle_action=request.bundle_action,
        chain=request.chain,
        metadata={
            **request.metadata,
            "wallet_from_id": str(request.wallet_from_id),
            "wallet_to_id": str(request.wallet_to_id),
            "correlation_id": str(request.correlation_id),
            "instrument_from_id": str(request.instrument_from_id),
            "instrument_to_id": str(request.instrument_to_id),
        },
    )


def execute_trade(
    db: Session,
    request: TradeRequest,
    actor: Any,
) -> TradeExecutionResult:
    """Quote LI.FI leg with virtual wallet context — delegates to BundleLifiLegService."""
    from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import (
        BundleLifiLegService,
    )

    leg = trade_request_to_execution_leg(request)
    svc = BundleLifiLegService()
    exec_result: ExecutionResult = svc.execute_leg(db, leg, actor)

    swap_id_raw = exec_result.provider_order_id or exec_result.raw.get("swap_id")
    if swap_id_raw is None:
        raise ValueError("execute_trade_missing_swap_id")

    swap_id = UUID(str(swap_id_raw))
    swap_repo = PersonWalletSwapRepository()
    person_id = svc._person_id_for_client(db, request.client_id)
    swap = swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
    if swap is not None:
        scope_from, pf_from = portfolio_scope_from_wallet(db, request.wallet_from_id)
        scope_to, pf_to = portfolio_scope_from_wallet(db, request.wallet_to_id)
        swap_repo.append_audit(
            swap,
            {
                "event": WALLET_CONTEXT_EVENT,
                "wallet_from_id": str(request.wallet_from_id),
                "wallet_to_id": str(request.wallet_to_id),
                "correlation_id": str(request.correlation_id),
                "instrument_from_id": str(request.instrument_from_id),
                "instrument_to_id": str(request.instrument_to_id),
                "portfolio_scope_from": scope_from,
                "portfolio_id_from": str(pf_from) if pf_from else None,
                "portfolio_scope_to": scope_to,
                "portfolio_id_to": str(pf_to) if pf_to else None,
            },
        )

    requires_sig = bool(exec_result.raw.get("requires_client_signature"))
    status: str
    if exec_result.status == "completed":
        status = "confirmed"
    elif exec_result.status == "pending" and requires_sig:
        status = "awaiting_signature"
    else:
        status = str(exec_result.status)

    return TradeExecutionResult(
        swap_id=swap_id,
        leg_id=request.leg_id,
        status=status,  # type: ignore[arg-type]
        from_asset=exec_result.from_asset,
        to_asset=exec_result.to_asset,
        amount_from=exec_result.amount_from,
        amount_to=exec_result.amount_to,
        tx_hash=exec_result.tx_hash,
        requires_client_signature=requires_sig,
        raw=dict(exec_result.raw),
    )
