"""Service execute LI.FI — payload signable Privy, lifecycle swap."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.config import swaps_mock_mode
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_approval_service import (
    build_token_approval_payload,
    read_chain_ids_from_lifi_quote,
    resolve_lifi_status_bridge,
)
from services.lifi.lifi_client import LifiClient, LifiClientError
from services.lifi.lifi_actual_receive import (
    is_lifi_done_complete_substatus,
    is_lifi_partial_substatus,
    resolve_lifi_actual_receive_amount,
)
from services.lifi.lifi_swap_settlement import (
    swap_settlement_already_applied,
)
from services.lifi.lifi_validation_service import SwapValidationError
from services.lifi.schemas import SwapExecuteResponse, SwapStatusResponse, SwapTransactionPayload
from services.lifi.signing_wallet_service import (
    assert_locked_signing_wallet_match,
    read_signing_wallet_from_audit,
)
from services.lifi.swap_failure_enums import SwapFailureCode
from services.lifi.swap_trace_service import log_swap_trace
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.transaction_outbox.orchestrator_settle_enqueue import (
    maybe_enqueue_orchestrator_intent_settle,
    skip_legacy_swap_settlement_for_orchestrator,
)

logger = logging.getLogger(__name__)

EXECUTE_GRACE_SECONDS = 600

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

    @staticmethod
    def _on_swap_confirmed_orchestrator_side_effects(db: Session, swap) -> None:
        """W3/W4 — enqueue ``intent.settle`` pour swaps orchestrateur standalone CONFIRMED."""
        maybe_enqueue_orchestrator_intent_settle(db, swap)

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
        swap.expires_at = datetime.now(timezone.utc) + timedelta(seconds=EXECUTE_GRACE_SECONDS)
        signing_mode, signing_address = read_signing_wallet_from_audit(swap.audit_log)
        if signing_address:
            self._swap_repo.append_audit(
                swap,
                {
                    "event": "wallet_locked",
                    "signing_wallet_mode": signing_mode,
                    "signing_wallet_address": signing_address,
                },
            )
        self._swap_repo.append_audit(swap, {"event": "awaiting_signature"})
        from services.transaction_intents.lifi_intent_sync import on_swap_awaiting_signature

        on_swap_awaiting_signature(db, swap)
        log_swap_trace(
            db,
            swap,
            event="awaiting_signature",
            status=swap.status,
            source="lifi_execute.prepare",
        )
        db.commit()
        db.refresh(swap)

        transaction = _map_transaction_request(tx_req, swap.from_chain)
        token_approval = build_token_approval_payload(swap.lifi_quote_raw)
        if token_approval.required:
            self._swap_repo.append_audit(
                swap,
                {
                    "event": "token_approval_required",
                    "token_address": token_approval.token_address,
                    "spender_address": token_approval.spender_address,
                },
            )
            log_swap_trace(
                db,
                swap,
                event="approval_required",
                status=swap.status,
                source="lifi_execute.prepare",
            )
            db.commit()
            db.refresh(swap)
        return SwapExecuteResponse(
            swap_id=swap.id,
            status=swap.status,
            lifecycle_message=LIFECYCLE_MESSAGES[swap.status],
            transaction=transaction,
            lifi_tool=swap.lifi_tool,
            signing_wallet_mode=signing_mode,
            signing_wallet_address=signing_address,
            token_approval=token_approval,
        )

    def submit_signed_tx(
        self,
        db: Session,
        *,
        person_id: UUID,
        swap_id: UUID,
        tx_hash: str,
        signing_wallet_address: str | None = None,
    ) -> SwapStatusResponse:
        swap = self._get_active_swap(db, person_id=person_id, swap_id=swap_id)
        # BROADCASTING = signature serveur déjà diffusée on-chain (D1) → transition légitime
        # vers SUBMITTED. AWAITING_SIGNATURE = chemin signature client classique.
        if swap.status not in {
            SwapSessionStatus.AWAITING_SIGNATURE.value,
            SwapSessionStatus.BROADCASTING.value,
        }:
            raise SwapValidationError("swap.invalid_state", "Signature requise avant soumission")

        assert_locked_signing_wallet_match(
            swap,
            connected_wallet_address=signing_wallet_address,
        )

        clean_hash = tx_hash.strip()
        if swaps_mock_mode() or clean_hash.startswith("0xmock"):
            swap.status = SwapSessionStatus.CONFIRMED.value
            swap.tx_hash = clean_hash or f"0xmock{swap.id.hex[:16]}"
            swap.confirmed_at = datetime.now(timezone.utc)
            if skip_legacy_swap_settlement_for_orchestrator(db, swap):
                self._on_swap_confirmed_orchestrator_side_effects(db, swap)
                from services.transaction_intents.lifi_intent_sync import on_swap_confirmed

                on_swap_confirmed(db, swap)
                from services.transaction_attempts.dual_write import (
                    dual_write_lifi_swap_confirmed,
                    dual_write_lifi_swap_submitted,
                )

                dual_write_lifi_swap_submitted(db, swap, tx_hash=swap.tx_hash)
                dual_write_lifi_swap_confirmed(db, swap, tx_hash=swap.tx_hash)
            else:
                from services.settlement.swap_router import settle_confirmed_swap

                settle_result = settle_confirmed_swap(
                    db,
                    swap,
                    sync_source="lifi_mock_swap",
                    allow_mock_quote_amount=True,
                )
                if settle_result.settled:
                    self._swap_repo.append_audit(
                        swap,
                        {"event": "swap_settled", "tx_hash": swap.tx_hash, "source": "lifi_mock_swap"},
                    )
                    from services.transaction_intents.lifi_intent_sync import on_swap_confirmed

                    on_swap_confirmed(db, swap)
                elif settle_result.skipped and settle_result.reason:
                    self._swap_repo.append_audit(
                        swap,
                        {
                            "event": "settlement_blocked",
                            "reason": settle_result.reason,
                        },
                    )
                    from services.transaction_intents.lifi_intent_sync import on_swap_settlement_blocked

                    on_swap_settlement_blocked(db, swap, reason=settle_result.reason)
                    from services.transaction_attempts.dual_write import (
                        dual_write_lifi_swap_confirmed,
                        dual_write_lifi_swap_submitted,
                    )

                    dual_write_lifi_swap_submitted(db, swap, tx_hash=swap.tx_hash)
                    dual_write_lifi_swap_confirmed(db, swap, tx_hash=swap.tx_hash)
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
        from services.transaction_intents.lifi_intent_sync import on_swap_submitted

        on_swap_submitted(db, swap, tx_hash=clean_hash)
        from services.transaction_attempts.dual_write import dual_write_lifi_swap_submitted

        dual_write_lifi_swap_submitted(db, swap, tx_hash=clean_hash)
        log_swap_trace(
            db,
            swap,
            event="swap_submitted",
            status=swap.status,
            tx_hash=clean_hash,
            source="lifi_execute.submit",
        )
        log_swap_trace(
            db,
            swap,
            event="confirming",
            status=swap.status,
            tx_hash=clean_hash,
            source="lifi_execute.submit",
        )
        db.commit()
        db.refresh(swap)

        logger.info(
            "swap.submitted",
            extra={"swap_id": str(swap.id), "person_id": str(person_id), "tx_hash": clean_hash},
        )
        self.refresh_lifi_status(db, swap)
        db.refresh(swap)
        return self._build_status_response(swap)

    def record_token_approval(
        self,
        db: Session,
        *,
        person_id: UUID,
        swap_id: UUID,
        tx_hash: str,
        signing_wallet_address: str | None = None,
    ) -> SwapStatusResponse:
        swap = self._get_active_swap(db, person_id=person_id, swap_id=swap_id)
        if swap.status != SwapSessionStatus.AWAITING_SIGNATURE.value:
            raise SwapValidationError("swap.invalid_state", "Approval avant signature swap requise")

        assert_locked_signing_wallet_match(
            swap,
            connected_wallet_address=signing_wallet_address,
        )

        clean_hash = tx_hash.strip().lower()
        self._swap_repo.append_audit(
            swap,
            {"event": "approval_submitted", "tx_hash": clean_hash},
        )
        from services.transaction_intents.lifi_intent_sync import on_swap_approval_submitted

        on_swap_approval_submitted(db, swap, approval_tx_hash=clean_hash)
        from services.transaction_attempts.dual_write import dual_write_lifi_approval_submitted

        dual_write_lifi_approval_submitted(db, swap, approval_tx_hash=clean_hash)
        log_swap_trace(
            db,
            swap,
            event="approval_submitted",
            status=swap.status,
            tx_hash=clean_hash,
            source="lifi_execute.approval",
        )
        db.commit()
        db.refresh(swap)

        logger.info(
            "swap.approval_submitted",
            extra={"swap_id": str(swap.id), "person_id": str(person_id), "tx_hash": clean_hash},
        )
        return self._build_status_response(swap)

    def abandon_swap(
        self,
        db: Session,
        *,
        person_id: UUID,
        swap_id: UUID,
        reason: str | None = None,
        explicit_user_abandon: bool = False,
        failure_phase: str | None = None,
    ) -> SwapStatusResponse:
        if not explicit_user_abandon:
            raise SwapValidationError(
                "swap.abandon_requires_explicit",
                "Abandon explicite requis — utilisez /failure pour les erreurs d'exécution.",
            )

        swap = self._swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
        if swap is None:
            raise SwapValidationError("swap.not_found", "Swap introuvable")
        if swap.status in {
            SwapSessionStatus.CONFIRMED.value,
            SwapSessionStatus.SUBMITTED.value,
        }:
            raise SwapValidationError(
                "swap.invalid_state",
                "Impossible d’abandonner un swap déjà soumis",
            )
        if swap.status == SwapSessionStatus.FAILED.value:
            return self._build_status_response(swap)

        from services.lifi.swap_failure_service import record_swap_failure

        record_swap_failure(
            db,
            person_id=person_id,
            swap_id=swap_id,
            failure_phase=failure_phase or "quote",
            error_code=SwapFailureCode.USER_ABANDONED.value,
            technical_message=reason or "user_explicit_abandon",
        )
        db.refresh(swap)
        return self._build_status_response(swap)

    def get_status(self, db: Session, *, person_id: UUID, swap_id: UUID) -> SwapStatusResponse:
        swap = self._swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
        if swap is None:
            raise SwapValidationError("swap.not_found", "Swap introuvable")

        if self._swap_repo.mark_expired_if_needed(swap):
            self._swap_repo.append_audit(swap, {"event": "expired"})
            from services.lifi.lifi_swap_global_lock import release_lifi_swap_global_lock_on_terminal

            release_lifi_swap_global_lock_on_terminal(db, swap)
            db.commit()
            db.refresh(swap)
            return self._build_status_response(swap, db=db, person_id=person_id)

        if swap.status == SwapSessionStatus.SUBMITTED.value:
            self.refresh_lifi_status(db, swap)
            db.refresh(swap)

        if swap.status == SwapSessionStatus.CONFIRMED.value:
            from services.settlement.swap_router import settle_confirmed_swap

            settle_confirmed_swap(db, swap)
            db.refresh(swap)

        return self._build_status_response(swap, db=db, person_id=person_id)

    def refresh_lifi_status(self, db: Session, swap) -> None:
        if swap.status != SwapSessionStatus.SUBMITTED.value or not swap.tx_hash:
            return

        from_chain_id, to_chain_id = read_chain_ids_from_lifi_quote(swap.lifi_quote_raw)
        bridge = resolve_lifi_status_bridge(
            lifi_tool=swap.lifi_tool,
            from_chain_id=from_chain_id,
            to_chain_id=to_chain_id,
        )

        try:
            payload = self._lifi.get_status(
                tx_hash=swap.tx_hash,
                bridge=bridge,
                from_chain=from_chain_id,
                to_chain=to_chain_id,
            )
        except LifiClientError as exc:
            logger.warning(
                "swap.lifi_status.error",
                extra={
                    "swap_id": str(swap.id),
                    "code": exc.code,
                    "bridge": bridge,
                    "from_chain": from_chain_id,
                    "to_chain": to_chain_id,
                },
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

        from services.transaction_intents.lifi_intent_sync import (
            on_swap_confirmed,
            on_swap_failed,
            on_swap_lifi_poll,
            on_swap_settlement_blocked,
        )

        if lifi_status in {"", "NOT_FOUND", "PENDING", "INVALID"}:
            on_swap_lifi_poll(db, swap, lifi_status=lifi_status, substatus=substatus)
            db.commit()
            return

        on_swap_lifi_poll(db, swap, lifi_status=lifi_status, substatus=substatus)

        if lifi_status == "DONE":
            if is_lifi_partial_substatus(substatus):
                self._swap_repo.append_audit(
                    swap,
                    {
                        "event": "partial_confirmed",
                        "lifi_status": lifi_status,
                        "substatus": substatus,
                        "substatus_message": substatus_message,
                    },
                )
                db.commit()
                return

            if substatus == "REFUNDED":
                swap.status = SwapSessionStatus.FAILED.value
                swap.error_message = substatus_message or "Swap remboursé sur la chaîne source"
                on_swap_failed(db, swap)
                db.commit()
                return

            if not is_lifi_done_complete_substatus(substatus):
                self._swap_repo.append_audit(
                    swap,
                    {
                        "event": "settlement_blocked",
                        "reason": "unknown_lifi_substatus",
                        "substatus": substatus,
                    },
                )
                on_swap_settlement_blocked(db, swap, reason="unknown_lifi_substatus")
                db.commit()
                return

            actual = resolve_lifi_actual_receive_amount(db, swap, lifi_status_payload=payload)
            if actual is None:
                swap.status = SwapSessionStatus.CONFIRMED.value
                swap.confirmed_at = datetime.now(timezone.utc)
                self._swap_repo.append_audit(
                    swap,
                    {
                        "event": "settlement_blocked",
                        "reason": "actual_amount_missing",
                        "lifi_status": lifi_status,
                        "substatus": substatus,
                    },
                )
                on_swap_settlement_blocked(db, swap, reason="actual_amount_missing")
                db.commit()
                return

            swap.status = SwapSessionStatus.CONFIRMED.value
            swap.confirmed_at = datetime.now(timezone.utc)

            if skip_legacy_swap_settlement_for_orchestrator(db, swap):
                self._on_swap_confirmed_orchestrator_side_effects(db, swap)
                on_swap_confirmed(db, swap)
                log_swap_trace(
                    db,
                    swap,
                    event="confirmed",
                    status=swap.status,
                    tx_hash=swap.tx_hash,
                    source="lifi_execute.refresh",
                )
            elif not swap_settlement_already_applied(swap):
                from services.settlement.swap_router import settle_confirmed_swap

                settle_result = settle_confirmed_swap(
                    db,
                    swap,
                    sync_source="lifi_swap",
                    actual_receive=actual,
                    lifi_status_payload=payload,
                )
                if settle_result.settled:
                    self._swap_repo.append_audit(
                        swap,
                        {
                            "event": "swap_settled",
                            "tx_hash": swap.tx_hash,
                            "source": "lifi_swap",
                            "actual_receive_amount": str(actual.amount),
                            "actual_receive_source": actual.source,
                        },
                    )
                    on_swap_confirmed(db, swap)
                    log_swap_trace(
                        db,
                        swap,
                        event="confirmed",
                        status=swap.status,
                        tx_hash=swap.tx_hash,
                        source="lifi_execute.refresh",
                    )
                elif settle_result.skipped and settle_result.reason:
                    self._swap_repo.append_audit(
                        swap,
                        {
                            "event": "settlement_blocked",
                            "reason": settle_result.reason,
                        },
                    )
                    on_swap_settlement_blocked(db, swap, reason=settle_result.reason)
                    log_swap_trace(
                        db,
                        swap,
                        event="reconciliation_required",
                        status=swap.status,
                        error_code=settle_result.reason,
                        tx_hash=swap.tx_hash,
                        source="lifi_execute.refresh",
                    )
            else:
                on_swap_confirmed(db, swap)
                self._on_swap_confirmed_orchestrator_side_effects(db, swap)
                log_swap_trace(
                    db,
                    swap,
                    event="confirmed",
                    status=swap.status,
                    tx_hash=swap.tx_hash,
                    source="lifi_execute.refresh",
                )
            from services.transaction_attempts.dual_write import dual_write_lifi_swap_confirmed

            dual_write_lifi_swap_confirmed(db, swap, tx_hash=swap.tx_hash)
        elif lifi_status == "FAILED":
            swap.status = SwapSessionStatus.FAILED.value
            swap.error_message = substatus_message or f"Swap LI.FI échoué ({substatus or 'FAILED'})"
            on_swap_failed(db, swap)
            from services.transaction_attempts.dual_write import dual_write_lifi_swap_confirmed

            dual_write_lifi_swap_confirmed(
                db,
                swap,
                tx_hash=swap.tx_hash,
                failed=True,
                error_message=swap.error_message,
            )

        db.commit()

    def _build_status_response(
        self,
        swap,
        *,
        db: Session | None = None,
        person_id: UUID | None = None,
    ) -> SwapStatusResponse:
        lifecycle = LIFECYCLE_MESSAGES.get(swap.status, swap.status)
        if swap.status == SwapSessionStatus.SUBMITTED.value:
            lifecycle = "Bridge in progress..."

        # PR4 — enrichissement front (mode autoritaire / file). Calculé uniquement quand
        # le contexte (db + person) est fourni (chemin GET status). Les autres appelants
        # (submit/approval/abandon) gardent les défauts (False / None) — non utilisés en
        # mode autoritaire (le front n'appelle jamais ces routes).
        server_authoritative = False
        queue_state = None
        if db is not None and person_id is not None:
            from services.lifi.orchestrator_allowlist import (
                lifi_authoritative_execution_enabled_for_person,
            )

            server_authoritative = lifi_authoritative_execution_enabled_for_person(
                db, person_id
            )
            if server_authoritative:
                from services.lifi.swap_queue_state import compute_swap_queue_state

                queue_state = compute_swap_queue_state(db, swap, person_id=person_id)

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
            server_authoritative=server_authoritative,
            queue_state=queue_state,
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
