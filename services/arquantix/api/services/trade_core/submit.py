"""Unified trade submit — swap portail + bundle legs (ADR 008 Phase 2)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.lifi_execute_service import LifiExecuteService
from services.lifi.schemas import SwapStatusResponse
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.portfolio_engine.bundle_execution.bundle_lifi_api import leg_from_swap_audit
from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import BundleLifiLegService
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)


def submit_signed_trade(
    db: Session,
    *,
    person_id: UUID,
    swap_id: UUID,
    tx_hash: str,
    signing_wallet_address: str | None = None,
) -> SwapStatusResponse | dict:
    """Submit tx — bundle legs get full PE settlement via BundleLifiLegService."""
    swap_repo = PersonWalletSwapRepository()
    swap = swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
    if swap is None:
        raise ValueError("swap_not_found")

    if is_bundle_internal_swap(swap):
        leg = leg_from_swap_audit(swap)
        if leg is None:
            raise ValueError("bundle_leg_context_missing")
        svc = BundleLifiLegService()
        result = svc.submit_leg_tx(
            db,
            leg=leg,
            person_id=person_id,
            swap_id=swap_id,
            tx_hash=tx_hash,
        )
        return {
            "leg_id": result.leg_id,
            "status": result.status,
            "swap_id": str(swap_id),
            "tx_hash": result.tx_hash,
            "amount_to": str(result.amount_to) if result.amount_to is not None else None,
            "bundle_leg": True,
        }

    execute_svc = LifiExecuteService()
    return execute_svc.submit_signed_tx(
        db,
        person_id=person_id,
        swap_id=swap_id,
        tx_hash=tx_hash,
        signing_wallet_address=signing_wallet_address,
    )
