"""Settlement PE bundle pour swaps LI.FI confirmés — idempotent et ré-essayable."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.bundle_lifi_api import leg_from_swap_audit
from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import (
    BundleLifiLegService,
)
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.portfolio_engine.bundle_execution.pe_settlement import swap_confirmed

logger = logging.getLogger(__name__)

SETTLEMENT_RECEIPT_EVENT = "bundle_pe_settlement_receipt"


def _audit_events(swap: PersonWalletSwap) -> list[dict[str, Any]]:
    audit = swap.audit_log
    if not isinstance(audit, list):
        return []
    return [e for e in audit if isinstance(e, dict)]


def swap_has_pe_settlement_receipt(swap: PersonWalletSwap) -> bool:
    return any(e.get("event") == SETTLEMENT_RECEIPT_EVENT for e in _audit_events(swap))


def swap_pe_atoms_flagged(swap: PersonWalletSwap) -> bool:
    return any(e.get("event") == "bundle_pe_atoms_applied" for e in _audit_events(swap))


def swap_needs_pe_settlement(swap: PersonWalletSwap) -> bool:
    """True si swap bundle confirmé sans reçu de settlement PE complet."""
    if not swap_confirmed(swap):
        return False
    if not is_bundle_internal_swap(swap):
        return False
    if leg_from_swap_audit(swap) is None:
        return False
    if swap_has_pe_settlement_receipt(swap):
        return False
    return True


def try_settle_confirmed_bundle_swap(
    db: Session,
    swap: PersonWalletSwap,
    *,
    force: bool = False,
) -> bool:
    """Applique le settlement PE si nécessaire. Retourne True si settled ou déjà OK."""
    if not swap_needs_pe_settlement(swap) and not force:
        return swap_has_pe_settlement_receipt(swap)

    leg = leg_from_swap_audit(swap)
    if leg is None:
        return False

    svc = BundleLifiLegService()
    if not force and svc._pe_atoms_already_applied(swap) and swap_has_pe_settlement_receipt(swap):
        return True

    try:
        svc._apply_post_confirmation(db, leg=leg, swap=swap)
        return True
    except Exception:
        logger.exception(
            "bundle_swap_pe_settlement_failed swap=%s leg=%s",
            swap.id,
            leg.leg_id,
        )
        return False


def settle_swaps_for_v3_leg_results(
    db: Session,
    results: list[Any],
) -> None:
    """Tente le settlement PE pour chaque leg V3 ayant un swap_id."""
    for row in results:
        swap_id = getattr(row, "swap_id", None)
        if not swap_id:
            continue
        try:
            swap_uuid = UUID(str(swap_id))
        except (TypeError, ValueError):
            continue
        swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap_uuid).first()
        if swap is None:
            continue
        try_settle_confirmed_bundle_swap(db, swap)
