"""Indexation minimale Base — ERC20 Transfer + natif vers wallets connus."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.assets import ASSET_PRECISION
from services.privy_wallet.asset_mapping import normalize_evm_address
from services.privy_wallet.deposit_backfill import fetch_transaction, fetch_transaction_receipt
from services.privy_wallet.enums import PersonWalletDepositStatus
from services.privy_wallet.evm_chain_config import resolve_chain_rpc_url
from services.privy_wallet.evm_rpc_client import (
    EvmRpcError,
    parse_erc20_transfers_from_receipt,
    parse_native_transfer_from_tx,
)
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import PersonCryptoWalletRepository

from .repository import RawOnChainEventRepository

logger = logging.getLogger(__name__)


def _amount_atomic(transfer: dict[str, Any]) -> int:
    if transfer.get("amount_atomic") is not None:
        return int(transfer["amount_atomic"])
    asset = str(transfer.get("asset") or "ETH").upper()
    precision = ASSET_PRECISION.get(asset, 18)
    amount = Decimal(str(transfer.get("amount") or 0))
    return int(amount * (Decimal(10) ** precision))


def index_transfers_from_tx(
    db: Session,
    *,
    chain_id: int,
    tx_hash: str,
    wallet_address: str,
) -> list[dict[str, Any]]:
    """
    Parse un receipt et enregistre les transferts entrants vers ``wallet_address``.

    Idempotent via ``raw_onchain_events`` (chain_id, tx_hash, log_index).
    """
    rpc_url = resolve_chain_rpc_url(chain_id)
    if not rpc_url:
        raise ValueError(f"RPC non configuré pour chain_id={chain_id}")

    normalized_wallet = normalize_evm_address(wallet_address) or wallet_address
    tx_hash_norm = str(tx_hash).strip().lower()
    if not tx_hash_norm.startswith("0x"):
        tx_hash_norm = f"0x{tx_hash_norm}"

    receipt = fetch_transaction_receipt(rpc_url, tx_hash_norm)
    tx = fetch_transaction(rpc_url, tx_hash_norm)

    transfers: list[dict[str, Any]] = []
    transfers.extend(
        parse_erc20_transfers_from_receipt(
            receipt,
            chain_id=chain_id,
            wallet_address=normalized_wallet,
        )
    )
    native = parse_native_transfer_from_tx(
        tx,
        chain_id=chain_id,
        wallet_address=normalized_wallet,
    )
    if native:
        transfers.append(native)

    results: list[dict[str, Any]] = []
    for transfer in transfers:
        event_type = "native_transfer" if not transfer.get("contract_address") else "erc20_transfer"
        row, created = RawOnChainEventRepository.insert_if_absent(
            db,
            data={
                "chain_id": chain_id,
                "block_number": transfer.get("block_number"),
                "tx_hash": transfer.get("tx_hash") or tx_hash_norm,
                "log_index": int(transfer.get("log_index") or 0),
                "contract_address": transfer.get("contract_address"),
                "event_type": event_type,
                "wallet_address": normalized_wallet,
                "asset": str(transfer["asset"]).upper(),
                "amount_raw": _amount_atomic(transfer),
                "payload_json": {"transfer": transfer, "source": "base_transfer_indexer"},
            },
        )
        results.append(
            {
                "event_id": str(row.id),
                "created": created,
                "tx_hash": row.tx_hash,
                "log_index": row.log_index,
                "asset": row.asset,
                "amount_raw": str(row.amount_raw),
            }
        )
    return results


def index_deposit_tx_hashes_for_wallet(
    db: Session,
    *,
    person_id: UUID,
    wallet_address: str,
    chain_id: int,
) -> dict[str, Any]:
    """Re-joue l'indexation pour chaque tx_hash distinct des dépôts confirmés du wallet."""
    wallet = PersonCryptoWalletRepository.find_active_by_address(db, wallet_address)
    if wallet is None or wallet.person_id != person_id:
        raise ValueError("Wallet introuvable ou person_id incompatible")

    rows = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.person_id == person_id,
            PersonWalletDeposit.person_crypto_wallet_id == wallet.id,
            PersonWalletDeposit.status == PersonWalletDepositStatus.CONFIRMED.value,
            PersonWalletDeposit.chain_id == chain_id,
        )
        .order_by(PersonWalletDeposit.created_at.asc())
        .all()
    )

    seen_tx: set[str] = set()
    indexed: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for deposit in rows:
        tx = str(deposit.tx_hash or "").strip().lower()
        if not tx or tx in seen_tx or tx.startswith("0xsim"):
            continue
        seen_tx.add(tx)
        try:
            events = index_transfers_from_tx(
                db,
                chain_id=chain_id,
                tx_hash=tx,
                wallet_address=wallet_address,
            )
            indexed.append({"tx_hash": tx, "events": events})
        except (EvmRpcError, ValueError) as exc:
            errors.append({"tx_hash": tx, "error": str(exc)})
            logger.warning("indexer.tx_failed", extra={"tx_hash": tx, "error": str(exc)})

    return {
        "tx_count": len(seen_tx),
        "indexed": indexed,
        "errors": errors,
    }
