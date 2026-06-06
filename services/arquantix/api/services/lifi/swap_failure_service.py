"""Enregistrement des échecs swap — audit trail sans masquage."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_validation_service import SwapValidationError
from services.lifi.swap_failure_enums import SwapFailureCode, SwapFailurePhase
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.lifi.swap_trace_service import log_swap_trace
from services.transaction_intents.lifi_intent_sync import on_swap_failed

logger = logging.getLogger(__name__)

_USER_FACING_MESSAGES: dict[str, str] = {
    SwapFailureCode.USER_REJECTED_SIGNATURE.value: "Signature refusée dans le wallet.",
    SwapFailureCode.USER_REJECTED_APPROVAL.value: "Approbation refusée dans le wallet.",
    SwapFailureCode.USER_ABANDONED.value: "Échange annulé.",
    SwapFailureCode.WALLET_ERROR.value: "Erreur wallet — réessayez ou reconnectez votre wallet.",
    SwapFailureCode.WALLET_MISMATCH.value: "Le wallet connecté ne correspond plus au devis — refaites une estimation.",
    SwapFailureCode.RPC_ERROR.value: "Réseau blockchain indisponible — réessayez dans quelques instants.",
    SwapFailureCode.LIFI_ERROR.value: "Route d'échange indisponible — refaites une estimation.",
    SwapFailureCode.QUOTE_EXPIRED.value: "Devis expiré — refaites une estimation.",
    SwapFailureCode.INSUFFICIENT_FUNDS.value: "Solde insuffisant pour cet échange.",
    SwapFailureCode.PRICE_CHANGED.value: "Le prix a changé — vérifiez le récapitulatif.",
    SwapFailureCode.UNKNOWN_ERROR.value: "Échange impossible — réessayez.",
}


def user_facing_failure_message(error_code: str) -> str:
    return _USER_FACING_MESSAGES.get(error_code, _USER_FACING_MESSAGES[SwapFailureCode.UNKNOWN_ERROR.value])


_VALID_FAILURE_PHASES = frozenset(phase.value for phase in SwapFailurePhase)
_VALID_ERROR_CODES = frozenset(code.value for code in SwapFailureCode)


def validate_swap_failure_payload(*, failure_phase: str, error_code: str) -> None:
    """Valide failure_phase et error_code contre les enums connus."""
    phase = (failure_phase or "").strip()
    code = (error_code or "").strip()
    if phase not in _VALID_FAILURE_PHASES:
        raise SwapValidationError(
            "swap.invalid_failure_phase",
            f"Phase d'échec invalide : {phase or '(vide)'}",
        )
    if code not in _VALID_ERROR_CODES:
        raise SwapValidationError(
            "swap.invalid_error_code",
            f"Code d'erreur invalide : {code or '(vide)'}",
        )


def record_swap_failure(
    db: Session,
    *,
    person_id: UUID,
    swap_id: UUID,
    failure_phase: str,
    error_code: str,
    technical_message: str | None = None,
    wallet_address: str | None = None,
) -> None:
    """Persiste un échec sans écraser un swap déjà soumis ou confirmé."""
    validate_swap_failure_payload(failure_phase=failure_phase, error_code=error_code)

    repo = PersonWalletSwapRepository()
    swap = repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
    if swap is None:
        raise SwapValidationError("swap.not_found", "Swap introuvable")

    if swap.status in {
        SwapSessionStatus.SUBMITTED.value,
        SwapSessionStatus.CONFIRMED.value,
    }:
        logger.warning(
            "swap.failure.skipped_terminal",
            extra={"swap_id": str(swap_id), "status": swap.status, "error_code": error_code},
        )
        return

    user_msg = user_facing_failure_message(error_code)
    swap.status = SwapSessionStatus.FAILED.value
    swap.error_message = user_msg
    repo.append_audit(
        swap,
        {
            "event": "execution_failed",
            "failure_phase": failure_phase,
            "error_code": error_code,
            "technical_message": (technical_message or "")[:2000],
            "wallet_address": wallet_address,
        },
    )
    on_swap_failed(db, swap)
    log_swap_trace(
        db,
        swap,
        event="failed",
        status=SwapSessionStatus.FAILED.value,
        error_code=error_code,
        message=user_msg,
        metadata_patch={
            "failure_phase": failure_phase,
            "technical_message": (technical_message or "")[:500],
        },
        source="swap_failure_service",
    )
    db.commit()
    db.refresh(swap)
    logger.info(
        "swap.failure.recorded",
        extra={
            "swap_id": str(swap_id),
            "failure_phase": failure_phase,
            "error_code": error_code,
        },
    )
