"""Backfill historique Li.FI → cost_basis_executions (idempotent)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.cost_basis.ingest_lifi import ingest_lifi_swap_settlement
from services.cost_basis.lifi_execution_ids import swap_fully_ingested
from services.cost_basis.lifi_swap_amounts import resolve_lifi_swap_amount_out
from services.cost_basis.repository import CostBasisExecutionRepository
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_actual_receive import _resolve_swap_wallet
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
    swap_has_strong_bundle_batch_context,
)

logger = logging.getLogger(__name__)

_CONFIRMED_STATUSES = frozenset({SwapSessionStatus.CONFIRMED.value})


@dataclass
class BackfillLifiSwapOutcome:
    swap_id: str
    person_id: str
    from_asset: str
    to_asset: str
    status: str
    reason: str
    rows_created: int = 0
    amount_out: Optional[str] = None
    amount_out_source: Optional[str] = None
    error: Optional[str] = None


@dataclass
class BackfillLifiResult:
    dry_run: bool
    scanned: int = 0
    eligible: int = 0
    ingested: int = 0
    rows_created: int = 0
    ignored: int = 0
    errors: int = 0
    outcomes: list[BackfillLifiSwapOutcome] = field(default_factory=list)
    error_details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "scanned": self.scanned,
            "eligible": self.eligible,
            "ingested": self.ingested,
            "rows_created": self.rows_created,
            "ignored": self.ignored,
            "errors": self.errors,
            "outcomes": [
                {
                    "swap_id": o.swap_id,
                    "person_id": o.person_id,
                    "from_asset": o.from_asset,
                    "to_asset": o.to_asset,
                    "status": o.status,
                    "reason": o.reason,
                    "rows_created": o.rows_created,
                    "amount_out": o.amount_out,
                    "amount_out_source": o.amount_out_source,
                    "error": o.error,
                }
                for o in self.outcomes
            ],
            "error_details": self.error_details,
        }


def _query_confirmed_swaps(
    db: Session,
    *,
    person_id: Optional[UUID] = None,
    client_id: Optional[UUID] = None,
    asset: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[PersonWalletSwap]:
    q = db.query(PersonWalletSwap).filter(
        PersonWalletSwap.status.in_(_CONFIRMED_STATUSES),
    )
    if person_id is not None:
        q = q.filter(PersonWalletSwap.person_id == person_id)
    if client_id is not None:
        from database import PersonCryptoWallet

        person_ids = [
            row[0]
            for row in db.query(PersonCryptoWallet.person_id)
            .filter(PersonCryptoWallet.pe_client_id == client_id)
            .distinct()
            .all()
        ]
        if not person_ids:
            return []
        q = q.filter(PersonWalletSwap.person_id.in_(person_ids))
    if asset is not None:
        asset_u = asset.upper()
        q = q.filter(
            (PersonWalletSwap.from_asset == asset_u) | (PersonWalletSwap.to_asset == asset_u)
        )
    q = q.order_by(
        PersonWalletSwap.confirmed_at.asc().nullsfirst(),
        PersonWalletSwap.created_at.asc(),
    )
    if limit is not None and limit > 0:
        q = q.limit(limit)
    return q.all()


def run_lifi_cost_basis_backfill(
    db: Session,
    *,
    dry_run: bool = True,
    person_id: Optional[UUID] = None,
    client_id: Optional[UUID] = None,
    asset: Optional[str] = None,
    limit: Optional[int] = None,
    allow_onchain_resolve: bool = False,
    allow_mock_quote_amount: bool = False,
) -> BackfillLifiResult:
    """Scanne les swaps Li.FI confirmés et ingère les cost basis manquants."""
    repo = CostBasisExecutionRepository()
    result = BackfillLifiResult(dry_run=dry_run)
    swaps = _query_confirmed_swaps(
        db,
        person_id=person_id,
        client_id=client_id,
        asset=asset,
        limit=limit,
    )
    result.scanned = len(swaps)

    for swap in swaps:
        swap_id = str(swap.id)
        from_asset = str(swap.from_asset).upper()
        to_asset = str(swap.to_asset).upper()

        if is_bundle_internal_swap(swap) or swap_has_strong_bundle_batch_context(swap):
            result.ignored += 1
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="ignored",
                    reason="bundle_internal",
                )
            )
            continue

        if swap_fully_ingested(db, swap, repo=repo):
            result.ignored += 1
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="ignored",
                    reason="already_ingested",
                )
            )
            continue

        result.eligible += 1

        try:
            wallet = _resolve_swap_wallet(db, swap)
        except Exception as exc:
            result.errors += 1
            result.error_details.append({"swap_id": swap_id, "stage": "wallet", "error": str(exc)})
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="error",
                    reason="wallet_missing",
                    error=str(exc),
                )
            )
            continue

        if wallet.pe_client_id is None:
            result.ignored += 1
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="ignored",
                    reason="missing_pe_client_id",
                )
            )
            continue

        try:
            amount_out, amount_source = resolve_lifi_swap_amount_out(
                db,
                swap,
                allow_onchain_resolve=allow_onchain_resolve,
                allow_mock_quote_amount=allow_mock_quote_amount,
            )
        except Exception as exc:
            result.errors += 1
            result.error_details.append({"swap_id": swap_id, "stage": "amount_out", "error": str(exc)})
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="error",
                    reason="amount_out_unavailable",
                    error=str(exc),
                )
            )
            continue

        if dry_run:
            result.ingested += 1
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="would_ingest",
                    reason="dry_run",
                    amount_out=str(amount_out),
                    amount_out_source=amount_source,
                )
            )
            logger.info(
                "cost_basis.backfill_lifi dry_run swap=%s %s→%s out=%s (%s)",
                swap_id,
                from_asset,
                to_asset,
                amount_out,
                amount_source,
            )
            continue

        try:
            created = ingest_lifi_swap_settlement(
                db,
                swap,
                wallet=wallet,
                amount_out=amount_out,
            )
            result.ingested += 1
            result.rows_created += created
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="ingested",
                    reason="ok",
                    rows_created=created,
                    amount_out=str(amount_out),
                    amount_out_source=amount_source,
                )
            )
            logger.info(
                "cost_basis.backfill_lifi ingested swap=%s rows=%s out=%s (%s)",
                swap_id,
                created,
                amount_out,
                amount_source,
            )
        except Exception as exc:
            result.errors += 1
            result.error_details.append({"swap_id": swap_id, "stage": "ingest", "error": str(exc)})
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="error",
                    reason="ingest_failed",
                    error=str(exc),
                    amount_out=str(amount_out),
                    amount_out_source=amount_source,
                )
            )
            logger.exception("cost_basis.backfill_lifi failed swap=%s", swap_id)

    return result
