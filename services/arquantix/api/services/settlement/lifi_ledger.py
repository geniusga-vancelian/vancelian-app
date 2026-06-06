"""Projection ledger LI.FI standalone — Settlement Layer S3b (debit + credit uniquement)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import (
    SWAP_LEDGER_LOG_INDEX_DEBIT_PREFERRED,
    _chain_id_for_swap,
    _create_swap_ledger_entry,
    _resolve_swap_wallet,
    swap_credit_idempotency_key,
    swap_debit_idempotency_key,
)
from services.lifi.lifi_validation_service import SwapValidationError
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.privy_wallet.enums import PersonWalletDirection
from services.privy_wallet.repository import PersonWalletDepositRepository
from services.settlement.constants import SETTLEMENT_LAYER_SYNC_SOURCE
from services.transaction_intents.enums import IntentProductType


class LifiStandaloneSettlementError(Exception):
    """Erreur métier settlement LI.FI standalone (mappée TERMINAL côté settle)."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def is_lifi_standalone_intent(intent: TransactionIntent) -> bool:
    return (intent.product_type or "").strip() == IntentProductType.LIFI_SWAP.value


def validate_lifi_standalone_eligible(intent: TransactionIntent, swap: PersonWalletSwap) -> None:
    if not is_lifi_standalone_intent(intent):
        raise LifiStandaloneSettlementError(
            "settlement.product_not_supported",
            "Produit hors périmètre S3b (LI.FI standalone uniquement)",
        )
    if is_bundle_internal_swap(swap):
        raise LifiStandaloneSettlementError(
            "settlement.bundle_internal_swap",
            "Swap bundle interne exclu du settlement S3b",
        )
    if (swap.status or "").upper() != SwapSessionStatus.CONFIRMED.value:
        raise LifiStandaloneSettlementError(
            "settlement.swap_not_confirmed",
            "Swap non confirmé — settlement ledger refusé",
        )
    if not str(swap.tx_hash or "").strip():
        raise LifiStandaloneSettlementError(
            "settlement.missing_tx_hash",
            "tx_hash requis pour settlement ledger",
        )


def _resolve_amount_out(intent: TransactionIntent, swap: PersonWalletSwap) -> Decimal:
    assets = intent.assets_json if isinstance(intent.assets_json, dict) else {}
    to_block = assets.get("to")
    if isinstance(to_block, dict) and to_block.get("amount") is not None:
        amount = Decimal(str(to_block["amount"]))
        if amount > 0:
            return amount
    if swap.estimated_receive is not None:
        amount = Decimal(str(swap.estimated_receive))
        if amount > 0:
            return amount
    raise LifiStandaloneSettlementError(
        "settlement.amount_out_missing",
        "Montant destination requis sur intent/linked swap",
    )


def _ledger_leg_exists(db: Session, idempotency_key: str) -> bool:
    return (
        PersonWalletDepositRepository.find_by_deposit_idempotency_key(db, idempotency_key)
        is not None
    )


def apply_lifi_standalone_ledger_settlement(
    db: Session,
    *,
    intent: TransactionIntent,
    swap: PersonWalletSwap,
) -> dict[str, Any]:
    """Débit source + crédit destination — exactly-once, sans PE ni cost basis."""
    validate_lifi_standalone_eligible(intent, swap)

    amount_in = Decimal(str(swap.amount_in))
    if amount_in <= 0:
        raise LifiStandaloneSettlementError(
            "settlement.invalid_amount_in",
            "Montant source invalide",
        )
    amount_out = _resolve_amount_out(intent, swap)

    wallet = _resolve_swap_wallet(db, swap)
    from_asset = str(swap.from_asset).upper()
    to_asset = str(swap.to_asset).upper()
    swap_id = str(swap.id)

    from services.privy_wallet.repository import PersonWalletBalanceRepository

    from_row = PersonWalletBalanceRepository().get_or_create_for_update(
        db,
        wallet_id=wallet.id,
        person_id=wallet.person_id,
        asset=from_asset,
    )
    available = Decimal(str(from_row.available_balance))
    if available < amount_in:
        raise LifiStandaloneSettlementError(
            "settlement.insufficient_balance",
            f"Solde {from_asset} insuffisant ({available} < {amount_in})",
        )

    debit_key = swap_debit_idempotency_key(swap_id)
    credit_key = swap_credit_idempotency_key(swap_id)
    debit_exists = _ledger_leg_exists(db, debit_key)
    credit_exists = _ledger_leg_exists(db, credit_key)

    settlement_meta = {
        "settlement_layer": "s3b",
        "intent_id": str(intent.id),
        "amount_out": str(amount_out),
    }

    from_chain_id = _chain_id_for_swap(str(swap.from_chain))
    to_chain_id = _chain_id_for_swap(str(swap.to_chain))

    wrote_debit = False
    wrote_credit = False

    if not debit_exists:
        wrote_debit = _create_swap_ledger_entry(
            db,
            swap=swap,
            wallet=wallet,
            direction=PersonWalletDirection.DEBIT.value,
            asset=from_asset,
            amount=amount_in,
            chain_id=from_chain_id,
            log_index=SWAP_LEDGER_LOG_INDEX_DEBIT_PREFERRED,
            idempotency_key=debit_key,
            sync_source=SETTLEMENT_LAYER_SYNC_SOURCE,
            settlement_meta=settlement_meta,
        )
        if not wrote_debit and not _ledger_leg_exists(db, debit_key):
            raise LifiStandaloneSettlementError(
                "settlement.debit_write_failed",
                "Échec écriture débit source",
            )

    if not credit_exists:
        wrote_credit = _create_swap_ledger_entry(
            db,
            swap=swap,
            wallet=wallet,
            direction=PersonWalletDirection.CREDIT.value,
            asset=to_asset,
            amount=amount_out,
            chain_id=to_chain_id,
            log_index=1,
            idempotency_key=credit_key,
            sync_source=SETTLEMENT_LAYER_SYNC_SOURCE,
            settlement_meta=settlement_meta,
        )
        if not wrote_credit and not _ledger_leg_exists(db, credit_key):
            raise LifiStandaloneSettlementError(
                "settlement.credit_write_failed",
                "Échec écriture crédit destination",
            )

    if not _ledger_leg_exists(db, debit_key) or not _ledger_leg_exists(db, credit_key):
        raise LifiStandaloneSettlementError(
            "settlement.incomplete_legs",
            "Jambes ledger incomplètes après projection",
        )

    return {
        "swap_id": swap_id,
        "wrote_debit": wrote_debit,
        "wrote_credit": wrote_credit,
        "debit_key": debit_key,
        "credit_key": credit_key,
    }


def count_swap_settlement_legs(db: Session, *, swap_id: UUID, person_id: UUID) -> dict[str, int]:
    """Compte débits/crédits swap par idempotency_key (tests S3b)."""
    swap_id_str = str(swap_id)
    deposit_repo = PersonWalletDepositRepository()
    debit = deposit_repo.find_by_deposit_idempotency_key(db, swap_debit_idempotency_key(swap_id_str))
    credit = deposit_repo.find_by_deposit_idempotency_key(db, swap_credit_idempotency_key(swap_id_str))
    return {
        "debit": 1 if debit is not None else 0,
        "credit": 1 if credit is not None else 0,
    }
