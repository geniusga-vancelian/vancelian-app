"""Backfill historique Li.FI bundle → cost_basis_executions (idempotent)."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.cost_basis.backfill_lifi import BackfillLifiResult, BackfillLifiSwapOutcome
from services.cost_basis.bundle_lifi_execution_ids import bundle_swap_fully_ingested
from services.cost_basis.ingest_bundle_lifi import ingest_bundle_lifi_swap_settlement
from services.cost_basis.lifi_swap_amounts import resolve_lifi_swap_amount_out
from services.cost_basis.repository import CostBasisExecutionRepository
from services.cost_basis.backfill_lifi import _query_confirmed_swaps
from services.lifi.lifi_actual_receive import _resolve_swap_wallet
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    bundle_portfolio_id_from_swap,
    is_bundle_internal_swap,
)

logger = logging.getLogger(__name__)


def run_bundle_lifi_cost_basis_backfill(
    db: Session,
    *,
    dry_run: bool = True,
    person_id: Optional[UUID] = None,
    client_id: Optional[UUID] = None,
    portfolio_id: Optional[UUID] = None,
    asset: Optional[str] = None,
    limit: Optional[int] = None,
    allow_onchain_resolve: bool = False,
    allow_mock_quote_amount: bool = False,
) -> BackfillLifiResult:
    """Scanne les swaps Li.FI bundle confirmés et ingère les cost basis manquants."""
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

        if not is_bundle_internal_swap(swap):
            result.ignored += 1
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="ignored",
                    reason="not_bundle_internal",
                )
            )
            continue

        pid_raw = bundle_portfolio_id_from_swap(swap)
        if pid_raw is None:
            result.ignored += 1
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="ignored",
                    reason="missing_portfolio_id",
                )
            )
            continue

        try:
            pid = UUID(str(pid_raw))
        except (ValueError, TypeError):
            result.ignored += 1
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="ignored",
                    reason="invalid_portfolio_id",
                )
            )
            continue

        if portfolio_id is not None and pid != portfolio_id:
            result.ignored += 1
            result.outcomes.append(
                BackfillLifiSwapOutcome(
                    swap_id=swap_id,
                    person_id=str(swap.person_id),
                    from_asset=from_asset,
                    to_asset=to_asset,
                    status="ignored",
                    reason="portfolio_filter_mismatch",
                )
            )
            continue

        if bundle_swap_fully_ingested(db, swap, repo=repo):
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
            continue

        try:
            created = ingest_bundle_lifi_swap_settlement(
                db,
                swap,
                wallet=wallet,
                amount_out=amount_out,
                portfolio_id=pid,
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
                )
            )
            logger.exception("cost_basis.backfill_bundle_lifi failed swap=%s", swap_id)

    return result
