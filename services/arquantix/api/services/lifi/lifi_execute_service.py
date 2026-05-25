"""Service execute LI.FI — payload signable Privy, lifecycle swap."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.config import swaps_mock_mode
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_client import LifiClient, LifiClientError
from services.lifi.lifi_mock_settlement import apply_mock_swap_settlement
from services.lifi.lifi_validation_service import SwapValidationError
from services.lifi.schemas import SwapExecuteResponse, SwapStatusResponse, SwapTransactionPayload
from services.lifi.signing_wallet_service import read_signing_wallet_from_audit
from services.lifi.swap_repository import PersonWalletSwapRepository

logger = logging.getLogger(__name__)

LIFECYCLE_MESSAGES: dict[str, str] = {
    SwapSessionStatus.PENDING.value: "Preparing route...",
    SwapSessionStatus.QUOTE_RECEIVED.value: "Quote ready",
    SwapSessionStatus.AWAITING_SIGNATURE.value: "Waiting signature...",
    SwapSessionStatus.SUBMITTED.value: "Bridge in progress...",
    SwapSessionStatus.CONFIRMED.value: "Swap completed",
    SwapSessionStatus.FAILED.value: "Swap failed",
    SwapSessionStatus.EXPIRED.value: "Quote expired",
}


class LifiExecuteService:
    def __init__(self, *, lifi_client: Optional[LifiClient] = None):
        self._swap_repo = PersonWalletSwapRepository()
        self._lifi = lifi_client or LifiClient()

    def prepare_execute(self, db: Session, *, person_id: UUID, swap_id: UUID) -> SwapExecuteResponse:
        swap = self._get_active_swap(db, person_id=person_id, swap_id=swap_id)
        if swap.status not in {
            SwapSessionStatus.QUOTE_RECEIVED.value,
            SwapSessionStatus.AWAITING_SIGNATURE.value,
        }:
            raise SwapValidationError("swap.invalid_state", f"État incompatible: {swap.status}")

        tx_req = swap.transaction_request
        if not isinstance(tx_req, dict):
            raise SwapValidationError("swap.missing_transaction", "Transaction LI.FI indisponible")

        swap.status = SwapSessionStatus.AWAITING_SIGNATURE.value
        self._swap_repo.append_audit(swap, {"event": "awaiting_signature"})
        db.commit()
        db.refresh(swap)

        transaction = _map_transaction_request(tx_req, swap.from_chain)
        signing_mode, signing_address = read_signing_wallet_from_audit(swap.audit_log)
        return SwapExecuteResponse(
            swap_id=swap.id,
            status=swap.status,
            lifecycle_message=LIFECYCLE_MESSAGES[swap.status],
            transaction=transaction,
            lifi_tool=swap.lifi_tool,
            signing_wallet_mode=signing_mode,
            signing_wallet_address=signing_address,
        )

    def submit_signed_tx(
        self,
        db: Session,
        *,
        person_id: UUID,
        swap_id: UUID,
        tx_hash: str,
    ) -> SwapStatusResponse:
        swap = self._get_active_swap(db, person_id=person_id, swap_id=swap_id)
        if swap.status != SwapSessionStatus.AWAITING_SIGNATURE.value:
            raise SwapValidationError("swap.invalid_state", "Signature requise avant soumission")

        clean_hash = tx_hash.strip()
        if swaps_mock_mode() or clean_hash.startswith("0xmock"):
            swap.status = SwapSessionStatus.CONFIRMED.value
            swap.tx_hash = clean_hash or f"0xmock{swap.id.hex[:16]}"
            swap.confirmed_at = datetime.now(timezone.utc)
            apply_mock_swap_settlement(db, swap)
            self._swap_repo.append_audit(
                swap,
                {"event": "mock_settled", "tx_hash": swap.tx_hash},
            )
            db.commit()
            db.refresh(swap)
            logger.info(
                "swap.mock_settled",
                extra={"swap_id": str(swap.id), "person_id": str(person_id)},
            )
            return self._build_status_response(swap)

        swap.status = SwapSessionStatus.SUBMITTED.value
        swap.tx_hash = clean_hash
        self._swap_repo.append_audit(swap, {"event": "submitted", "tx_hash": clean_hash})
        db.commit()
        db.refresh(swap)

        logger.info(
            "swap.submitted",
            extra={"swap_id": str(swap.id), "person_id": str(person_id), "tx_hash": clean_hash},
        )
        self.refresh_lifi_status(db, swap)
        db.refresh(swap)
        return self._build_status_response(swap)

    def get_status(self, db: Session, *, person_id: UUID, swap_id: UUID) -> SwapStatusResponse:
        swap = self._swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
        if swap is None:
            raise SwapValidationError("swap.not_found", "Swap introuvable")

        if self._swap_repo.mark_expired_if_needed(swap):
            self._swap_repo.append_audit(swap, {"event": "expired"})
            db.commit()
            db.refresh(swap)
            return self._build_status_response(swap)

        if swap.status == SwapSessionStatus.SUBMITTED.value:
            self.refresh_lifi_status(db, swap)
            db.refresh(swap)

        return self._build_status_response(swap)

    def refresh_lifi_status(self, db: Session, swap) -> None:
        if swap.status != SwapSessionStatus.SUBMITTED.value or not swap.tx_hash:
            return

        try:
            payload = self._lifi.get_status(
                tx_hash=swap.tx_hash,
                bridge=swap.lifi_tool,
            )
        except LifiClientError as exc:
            logger.warning(
                "swap.lifi_status.error",
                extra={"swap_id": str(swap.id), "code": exc.code},
            )
            return

        lifi_status = str(payload.get("status") or "").upper()
        substatus = str(payload.get("substatus") or "").upper()
        substatus_message = str(payload.get("substatusMessage") or "").strip()

        self._swap_repo.append_audit(
            swap,
            {
                "event": "lifi_status_poll",
                "lifi_status": lifi_status,
                "substatus": substatus,
            },
        )

        if lifi_status in {"", "NOT_FOUND", "PENDING", "INVALID"}:
            db.commit()
            return

        if lifi_status == "DONE":
            if substatus in {"COMPLETED", "PARTIAL", ""}:
                swap.status = SwapSessionStatus.CONFIRMED.value
                swap.confirmed_at = datetime.now(timezone.utc)
            elif substatus == "REFUNDED":
                swap.status = SwapSessionStatus.FAILED.value
                swap.error_message = substatus_message or "Swap remboursé sur la chaîne source"
            else:
                swap.status = SwapSessionStatus.CONFIRMED.value
                swap.confirmed_at = datetime.now(timezone.utc)
        elif lifi_status == "FAILED":
            swap.status = SwapSessionStatus.FAILED.value
            swap.error_message = substatus_message or f"Swap LI.FI échoué ({substatus or 'FAILED'})"

        db.commit()

    def _build_status_response(self, swap) -> SwapStatusResponse:
        lifecycle = LIFECYCLE_MESSAGES.get(swap.status, swap.status)
        if swap.status == SwapSessionStatus.SUBMITTED.value:
            lifecycle = "Bridge in progress..."
        return SwapStatusResponse(
            swap_id=swap.id,
            status=swap.status,
            lifecycle_message=lifecycle,
            from_asset=swap.from_asset,
            to_asset=swap.to_asset,
            from_chain=swap.from_chain,
            to_chain=swap.to_chain,
            amount_in=_fmt_decimal(swap.amount_in),
            estimated_receive=_fmt_decimal(swap.estimated_receive),
            tx_hash=swap.tx_hash,
            error_message=swap.error_message,
        )

    def _get_active_swap(self, db: Session, *, person_id: UUID, swap_id: UUID):
        swap = self._swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
        if swap is None:
            raise SwapValidationError("swap.not_found", "Swap introuvable")
        if self._swap_repo.mark_expired_if_needed(swap):
            db.commit()
            raise SwapValidationError("swap.expired", "Quote expirée — refaire une estimation")
        if swap.status == SwapSessionStatus.FAILED.value:
            raise SwapValidationError("swap.failed", swap.error_message or "Swap échoué")
        return swap


def _map_transaction_request(tx_req: dict[str, Any], from_chain: str) -> SwapTransactionPayload:
    chain_id = tx_req.get("chainId")
    if chain_id is None:
        from config.supported_swap_assets import SUPPORTED_SWAP_CHAINS

        chain_id = SUPPORTED_SWAP_CHAINS.get(from_chain, {}).get("lifi_chain_id", 1)
    return SwapTransactionPayload(
        chain_id=chain_id,
        to=str(tx_req.get("to") or ""),
        data=str(tx_req.get("data") or "0x"),
        value=str(tx_req.get("value") or "0"),
        gas_limit=_optional_str(tx_req.get("gasLimit") or tx_req.get("gas_limit")),
        gas_price=_optional_str(tx_req.get("gasPrice") or tx_req.get("gas_price")),
    )


def _optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _fmt_decimal(value) -> str:
    if value is None:
        return "0"
    from decimal import Decimal

    dec = Decimal(str(value))
    text = format(dec.normalize(), "f")
    return text.rstrip("0").rstrip(".") or "0"
