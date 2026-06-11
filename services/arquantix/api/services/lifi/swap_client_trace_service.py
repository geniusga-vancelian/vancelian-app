"""Traces client swap — audit append-only (debug exécution Privy embed)."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.lifi_validation_service import SwapValidationError
from services.lifi.swap_repository import PersonWalletSwapRepository

logger = logging.getLogger(__name__)


def record_swap_client_trace(
    db: Session,
    *,
    person_id: UUID,
    swap_id: UUID,
    step: str,
    phase: str | None = None,
    detail: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """Append-only — n'altère pas le statut swap."""
    repo = PersonWalletSwapRepository()
    swap = repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
    if swap is None:
        raise SwapValidationError("swap.not_found", "Swap introuvable")

    event: dict[str, str] = {"event": "client_trace", "step": step.strip()[:64]}
    if phase:
        event["phase"] = phase.strip()[:32]
    if detail:
        event["detail"] = detail.strip()[:500]
    if correlation_id:
        event["correlation_id"] = correlation_id.strip()[:128]

    repo.append_audit(swap, event)
    db.commit()
    logger.info(
        "swap.client_trace",
        extra={"swap_id": str(swap_id), "step": step, "phase": phase},
    )
