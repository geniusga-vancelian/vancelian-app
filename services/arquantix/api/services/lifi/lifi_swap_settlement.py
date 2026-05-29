"""Règlement ledger Privy après swap LI.FI confirmé (montant réel uniquement)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from config.supported_swap_assets import SUPPORTED_SWAP_CHAINS, normalize_chain_key
from database import PersonCryptoWallet
from services.lifi.lifi_actual_receive import (
    LifiActualReceiveResult,
    resolve_lifi_actual_receive_amount,
)
from services.lifi.lifi_validation_service import SwapValidationError
from services.lifi.signing_wallet_service import read_signing_wallet_from_audit
from services.privy_wallet.asset_mapping import normalize_evm_address
from services.privy_wallet.enums import PersonWalletDepositStatus, PersonWalletDirection
from services.privy_wallet.repository import (
    PersonCryptoWalletRepository,
    PersonWalletBalanceRepository,
    PersonWalletDepositRepository,
)

logger = logging.getLogger(__name__)


def _format_decimal(value: Decimal | object) -> str:
    d = Decimal(str(value))
    text = format(d.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


class SwapSettlementBlocked(Exception):
    """Settlement refusé — swap laissé pour réconciliation manuelle."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def swap_settlement_already_applied(swap) -> bool:
    audit = swap.audit_log
    if isinstance(audit, list):
        return any(isinstance(entry, dict) and entry.get("event") == "swap_settled" for entry in audit)
    return False


def _chain_id_for_swap(chain_key: str) -> int:
    normalized = normalize_chain_key(chain_key)
    meta = SUPPORTED_SWAP_CHAINS.get(normalized)
    if not meta:
        raise SwapValidationError("swap.invalid_chain", f"Chaîne swap inconnue: {chain_key}")
    return int(meta["lifi_chain_id"])


def _resolve_swap_wallet(db: Session, swap) -> PersonCryptoWallet:
    wallets = PersonCryptoWalletRepository.list_active_for_person(db, swap.person_id)
    if not wallets:
        raise SwapValidationError("swap.wallet_missing", "Aucun wallet lié pour ce swap")

    _, signing_address = read_signing_wallet_from_audit(swap.audit_log)
    if signing_address:
        target = normalize_evm_address(signing_address)
        for wallet in wallets:
            normalized = normalize_evm_address(wallet.address)
            if normalized and normalized.lower() == target.lower():
                return wallet

    for wallet in wallets:
        if (wallet.provider or "").strip().lower() == "privy":
            return wallet

    return wallets[0]


def _create_swap_ledger_entry(
    db: Session,
    *,
    swap,
    wallet: PersonCryptoWallet,
    direction: str,
    asset: str,
    amount: Decimal,
    chain_id: int,
    log_index: int,
    idempotency_key: str,
    sync_source: str,
    settlement_meta: dict[str, Any] | None = None,
) -> None:
    deposit_repo = PersonWalletDepositRepository()
    balance_repo = PersonWalletBalanceRepository()

    existing = deposit_repo.find_by_chain_tx(
        db,
        chain_id=chain_id,
        tx_hash=swap.tx_hash,
        log_index=log_index,
    )
    if existing is not None:
        return

    asset_u = asset.upper()
    amount_display = _format_decimal(amount)
    title = f"Échange {swap.from_asset.upper()} → {swap.to_asset.upper()}"
    subtitle_prefix = "−" if direction == PersonWalletDirection.DEBIT.value else "+"
    subtitle = f"{subtitle_prefix}{amount_display} {asset_u}"

    deposit_repo.create(
        db,
        data={
            "person_crypto_wallet_id": wallet.id,
            "person_id": wallet.person_id,
            "pe_client_id": wallet.pe_client_id,
            "privy_webhook_event_id": None,
            "transaction_kind": "crypto_swap",
            "direction": direction,
            "asset": asset_u,
            "amount": amount,
            "chain_type": "ethereum",
            "chain_id": chain_id,
            "tx_hash": swap.tx_hash,
            "log_index": log_index,
            "block_number": None,
            "from_address": wallet.address,
            "to_address": wallet.address,
            "confirmations": 1,
            "status": PersonWalletDepositStatus.CONFIRMED.value,
            "idempotency_key": idempotency_key,
            "title": title,
            "subtitle": subtitle,
            "metadata_json": {
                "swap_id": str(swap.id),
                "source": sync_source,
                "from_asset": str(swap.from_asset).upper(),
                "to_asset": str(swap.to_asset).upper(),
                "swap_amount_from": _format_decimal(swap.amount_in),
                "swap_amount_to_estimated": _format_decimal(swap.estimated_receive),
                "swap_amount_to": _format_decimal(amount),
                "amount_actual": _format_decimal(amount),
                **(settlement_meta or {}),
            },
            "confirmed_at": datetime.now(timezone.utc),
        },
    )

    balance_row = balance_repo.get_or_create_for_update(
        db,
        wallet_id=wallet.id,
        person_id=wallet.person_id,
        asset=asset_u,
    )
    delta = -amount if direction == PersonWalletDirection.DEBIT.value else amount
    balance_repo.increment_balance(db, balance_row, delta=delta, sync_source=sync_source)


def backfill_unsettled_confirmed_swaps(db: Session, *, person_id: UUID, limit: int = 20) -> int:
    """Applique le règlement ledger pour les swaps CONFIRMED historiques sans swap_settled."""
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.models import PersonWalletSwap
    from services.lifi.swap_repository import PersonWalletSwapRepository

    rows = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == person_id,
            PersonWalletSwap.status == SwapSessionStatus.CONFIRMED.value,
        )
        .order_by(PersonWalletSwap.confirmed_at.desc(), PersonWalletSwap.created_at.desc())
        .limit(limit)
        .all()
    )

    settled = 0
    swap_repo = PersonWalletSwapRepository()
    for swap in rows:
        if swap_settlement_already_applied(swap):
            continue
        try:
            apply_swap_settlement(db, swap, sync_source="lifi_swap_backfill")
        except SwapSettlementBlocked:
            continue
        swap_repo.append_audit(
            swap,
            {"event": "swap_settled", "tx_hash": swap.tx_hash, "source": "lifi_swap_backfill"},
        )
        settled += 1

    if settled:
        db.commit()
    return settled


def apply_swap_settlement(
    db: Session,
    swap,
    *,
    sync_source: str = "lifi_swap",
    amount_actual: Decimal | None = None,
    actual_receive: LifiActualReceiveResult | None = None,
    lifi_status_payload: dict[str, Any] | None = None,
    allow_mock_quote_amount: bool = False,
) -> None:
    """Débite l'actif source et crédite la destination (montant réel ``amount_actual`` uniquement)."""
    if swap_settlement_already_applied(swap):
        return

    tx_hash = str(swap.tx_hash or "").strip().lower()
    if not tx_hash:
        raise SwapValidationError("swap.missing_tx_hash", "Hash transaction requis pour le règlement")

    resolved = actual_receive
    if resolved is None and amount_actual is not None:
        if amount_actual <= 0:
            raise SwapSettlementBlocked(
                "actual_amount_missing",
                "Montant réel invalide pour le règlement.",
            )
        resolved = LifiActualReceiveResult(
            amount=amount_actual,
            source="caller_amount_actual",
            receive_tx_hash=tx_hash,
        )
    if resolved is None:
        resolved = resolve_lifi_actual_receive_amount(
            db,
            swap,
            lifi_status_payload=lifi_status_payload,
            allow_mock_quote_amount=allow_mock_quote_amount,
        )

    if resolved is None or resolved.amount <= 0:
        raise SwapSettlementBlocked(
            "actual_amount_missing",
            "Montant réellement reçu introuvable — règlement bloqué.",
        )

    wallet = _resolve_swap_wallet(db, swap)
    from_asset = str(swap.from_asset).upper()
    to_asset = str(swap.to_asset).upper()
    amount_in = Decimal(str(swap.amount_in))
    amount_out = resolved.amount

    if amount_in <= 0:
        raise SwapValidationError("swap.invalid_amounts", "Montant source invalide pour le règlement")

    settlement_meta = {
        "actual_receive_source": resolved.source,
        "actual_receive_amount": _format_decimal(resolved.amount),
    }
    if resolved.receive_tx_hash:
        settlement_meta["actual_receive_tx_hash"] = resolved.receive_tx_hash

    from_chain_id = _chain_id_for_swap(str(swap.from_chain))
    to_chain_id = _chain_id_for_swap(str(swap.to_chain))

    from_row = PersonWalletBalanceRepository().get_or_create_for_update(
        db,
        wallet_id=wallet.id,
        person_id=wallet.person_id,
        asset=from_asset,
    )
    available = Decimal(str(from_row.available_balance))
    if available < amount_in:
        from services.lifi.config import swaps_mock_mode

        if swaps_mock_mode():
            shortfall = amount_in - available
            PersonWalletBalanceRepository.increment_balance(
                db,
                from_row,
                delta=shortfall,
                sync_source="lifi_mock_ledger_top_up",
            )
            db.flush()
            available = Decimal(str(from_row.available_balance))
            logger.info(
                "lifi.mock_ledger_top_up asset=%s shortfall=%s available=%s",
                from_asset,
                shortfall,
                available,
            )
        if available < amount_in:
            raise SwapValidationError(
                "swap.insufficient_balance",
                f"Solde {from_asset} insuffisant pour le swap ({available} < {amount_in})",
            )

    swap_id = str(swap.id)
    credit_log_index = resolved.log_index if resolved.log_index is not None else 1

    _create_swap_ledger_entry(
        db,
        swap=swap,
        wallet=wallet,
        direction=PersonWalletDirection.DEBIT.value,
        asset=from_asset,
        amount=amount_in,
        chain_id=from_chain_id,
        log_index=0,
        idempotency_key=f"lifi-swap:{swap_id}:debit",
        sync_source=sync_source,
        settlement_meta=settlement_meta,
    )
    _create_swap_ledger_entry(
        db,
        swap=swap,
        wallet=wallet,
        direction=PersonWalletDirection.CREDIT.value,
        asset=to_asset,
        amount=amount_out,
        chain_id=to_chain_id,
        log_index=credit_log_index,
        idempotency_key=f"lifi-swap:{swap_id}:credit",
        sync_source=sync_source,
        settlement_meta=settlement_meta,
    )

    try:
        from services.cost_basis.ingest_lifi import ingest_lifi_swap_settlement

        ingest_lifi_swap_settlement(db, swap, wallet=wallet, amount_out=amount_out)
    except Exception:
        logger.exception(
            "cost_basis.lifi_ingest_failed swap_id=%s person_id=%s",
            swap_id,
            wallet.person_id,
        )
