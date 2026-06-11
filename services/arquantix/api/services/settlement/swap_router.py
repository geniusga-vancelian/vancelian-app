"""ADR 007 S1 — Settlement Router : routage post-CONFIRMED par scope comptable."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_actual_receive import LifiActualReceiveResult
from services.lifi.lifi_swap_settlement import (
    SwapSettlementBlocked,
    apply_swap_settlement,
)
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.portfolio_engine.bundle_execution.pe_settlement import swap_confirmed

logger = logging.getLogger(__name__)

SCOPE_SELF_TRADING = "self_trading"
SCOPE_BUNDLE_PORTFOLIO = "bundle_portfolio"
SCOPE_SKIPPED = "skipped"


@dataclass(frozen=True)
class SettleConfirmedSwapResult:
    settled: bool
    scope: str
    skipped: bool = False
    reason: str | None = None


def resolve_settlement_scope(swap: PersonWalletSwap) -> str:
    if is_bundle_internal_swap(swap):
        return SCOPE_BUNDLE_PORTFOLIO
    return SCOPE_SELF_TRADING


def settle_confirmed_swap(
    db: Session,
    swap: PersonWalletSwap,
    *,
    sync_source: str = "lifi_swap",
    amount_actual: Decimal | None = None,
    actual_receive: LifiActualReceiveResult | None = None,
    lifi_status_payload: dict[str, Any] | None = None,
    allow_mock_quote_amount: bool = False,
    force_bundle: bool = False,
) -> SettleConfirmedSwapResult:
    """Point d'entrée unique — route vers handler self-trading ou bundle PE."""
    if not swap_confirmed(swap):
        return SettleConfirmedSwapResult(
            settled=False,
            scope=SCOPE_SKIPPED,
            skipped=True,
            reason="swap_not_confirmed",
        )

    scope = resolve_settlement_scope(swap)

    if scope == SCOPE_BUNDLE_PORTFOLIO:
        from services.portfolio_engine.bundle_execution.bundle_swap_pe_settlement import (
            try_settle_confirmed_bundle_swap,
        )

        ok = try_settle_confirmed_bundle_swap(db, swap, force=force_bundle)
        if ok:
            from services.settlement.wallet_ledger import settle_trade_wallets

            settle_trade_wallets(db, swap)
        return SettleConfirmedSwapResult(
            settled=ok,
            scope=scope,
            skipped=not ok,
            reason=None if ok else "bundle_pe_settlement_failed",
        )

    try:
        apply_swap_settlement(
            db,
            swap,
            sync_source=sync_source,
            amount_actual=amount_actual,
            actual_receive=actual_receive,
            lifi_status_payload=lifi_status_payload,
            allow_mock_quote_amount=allow_mock_quote_amount,
        )
    except SwapSettlementBlocked as exc:
        logger.warning(
            "settlement_router_self_trading_blocked swap=%s code=%s",
            swap.id,
            exc.code,
        )
        return SettleConfirmedSwapResult(
            settled=False,
            scope=scope,
            skipped=True,
            reason=str(exc.code),
        )

    from services.settlement.wallet_ledger import settle_trade_wallets

    settle_trade_wallets(db, swap)
    return SettleConfirmedSwapResult(settled=True, scope=scope)


def swap_is_confirmed_status(swap: PersonWalletSwap) -> bool:
    return str(swap.status or "").upper() == SwapSessionStatus.CONFIRMED.value
