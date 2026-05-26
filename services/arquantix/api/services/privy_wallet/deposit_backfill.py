"""Backfill de dépôts Privy depuis la chain (tx hash ou scan Alchemy)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .asset_mapping import contract_for_asset, normalize_evm_address, parse_caip2_chain_id
from .evm_chain_config import resolve_chain_rpc_url
from .evm_rpc_client import (
    EvmRpcError,
    fetch_alchemy_asset_transfers_to_wallet,
    fetch_on_chain_asset_balance,
    fetch_transaction,
    fetch_transaction_receipt,
    parse_erc20_transfers_from_receipt,
    parse_native_transfer_from_tx,
)
from .repository import PersonCryptoWalletRepository, PersonWalletDepositRepository
from .webhook_service import FUNDS_DEPOSITED_EVENT, PrivyWebhookProcessor


class DepositBackfillError(ValueError):
    pass


def build_deposit_webhook_payload(transfer: dict[str, Any]) -> dict[str, Any]:
    from services.exchange.assets import ASSET_PRECISION

    chain_id = int(transfer["chain_id"])
    asset = str(transfer["asset"]).upper()
    contract = transfer.get("contract_address")
    if transfer.get("amount_atomic") is not None:
        amount_atomic = str(transfer["amount_atomic"])
    else:
        precision = ASSET_PRECISION.get(asset, 18)
        amount_atomic = str(int(Decimal(str(transfer["amount"])) * (Decimal(10) ** precision)))

    data: dict[str, Any] = {
        "to_address": transfer["to_address"],
        "from_address": transfer.get("from_address"),
        "transaction_hash": transfer["tx_hash"],
        "chain_id": f"eip155:{chain_id}",
        "amount": amount_atomic,
        "log_index": int(transfer.get("log_index") or 0),
        "block_number": transfer.get("block_number"),
        "confirmations": 12,
    }

    if contract:
        data["contract_address"] = contract
        data["asset"] = {"type": "erc20", "symbol": asset}
    else:
        data["asset"] = {"type": "native", "symbol": asset}

    return {
        "type": FUNDS_DEPOSITED_EVENT,
        "id": f"backfill_{uuid.uuid4().hex[:16]}",
        "idempotency_key": f"backfill_{transfer['tx_hash']}_{transfer.get('log_index', 0)}",
        "data": data,
    }


def ingest_transfer_as_deposit(
    db: Session,
    *,
    transfer: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    processor = PrivyWebhookProcessor()
    deposit_repo = PersonWalletDepositRepository()

    existing = deposit_repo.find_by_chain_tx(
        db,
        chain_id=int(transfer["chain_id"]),
        tx_hash=str(transfer["tx_hash"]).lower(),
        log_index=int(transfer.get("log_index") or 0),
    )
    if existing:
        return {
            "status": "already_ingested",
            "deposit_id": str(existing.id),
            "tx_hash": existing.tx_hash,
            "asset": existing.asset,
            "amount": str(existing.amount),
        }

    payload = build_deposit_webhook_payload(transfer)
    idempotency_key = payload["idempotency_key"]
    event = processor.store_raw_event(
        db,
        event_type=FUNDS_DEPOSITED_EVENT,
        payload=payload,
        svix_id=f"{source}_{uuid.uuid4().hex[:12]}",
        idempotency_key=idempotency_key,
        external_reference=str(transfer["tx_hash"]).lower(),
    )
    event_status = processor.process_event(db, event)
    deposit = deposit_repo.find_by_chain_tx(
        db,
        chain_id=int(transfer["chain_id"]),
        tx_hash=str(transfer["tx_hash"]).lower(),
        log_index=int(transfer.get("log_index") or 0),
    )
    return {
        "status": event_status,
        "event_id": str(event.id),
        "deposit_id": str(deposit.id) if deposit else None,
        "tx_hash": transfer["tx_hash"],
        "asset": transfer["asset"],
        "amount": str(transfer["amount"]),
        "error": event.error_message,
    }


def backfill_deposit_from_tx_hash(
    db: Session,
    *,
    person_id: UUID,
    chain_id: int,
    tx_hash: str,
    wallet_address: str | None = None,
) -> list[dict[str, Any]]:
    rpc_url = resolve_chain_rpc_url(chain_id)
    if not rpc_url:
        raise DepositBackfillError(f"RPC non configuré pour chain_id={chain_id}")

    wallet_repo = PersonCryptoWalletRepository()
    wallets = wallet_repo.list_active_for_person(db, person_id)
    if not wallets:
        raise DepositBackfillError("Aucun wallet Privy actif pour cette personne")

    if wallet_address:
        wallet = wallet_repo.find_active_by_address(db, wallet_address)
        if wallet is None or wallet.person_id != person_id:
            raise DepositBackfillError("Wallet introuvable pour cette personne")
        target_address = wallet.address
    else:
        target_address = wallets[0].address

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
            wallet_address=target_address,
        )
    )
    native = parse_native_transfer_from_tx(
        tx,
        chain_id=chain_id,
        wallet_address=target_address,
    )
    if native:
        transfers.append(native)

    if not transfers:
        raise DepositBackfillError(
            "Aucun transfert entrant reconnu vers le wallet sur cette transaction."
        )

    results = [
        ingest_transfer_as_deposit(db, transfer=t, source="admin_backfill")
        for t in transfers
    ]
    return results


def alchemy_transfer_to_internal(
    raw: dict[str, Any],
    *,
    chain_id: int,
    wallet_address: str,
) -> dict[str, Any] | None:
    to_addr = normalize_evm_address(raw.get("to"))
    if to_addr != normalize_evm_address(wallet_address):
        return None

    category = str(raw.get("category") or "").lower()
    tx_hash = str(raw.get("hash") or "").lower()
    if not tx_hash.startswith("0x"):
        tx_hash = f"0x{tx_hash}"

    block_num = raw.get("blockNum")
    block_number = int(block_num, 16) if isinstance(block_num, str) and block_num.startswith("0x") else None

    if category == "external":
        value = raw.get("value")
        if value is None:
            return None
        amount = Decimal(str(value))
        if amount <= 0:
            return None
        return {
            "asset": "ETH",
            "amount": amount,
            "amount_atomic": str(int(amount * Decimal(10) ** 18)),
            "from_address": normalize_evm_address(raw.get("from")),
            "to_address": to_addr,
            "contract_address": None,
            "tx_hash": tx_hash,
            "log_index": 0,
            "block_number": block_number,
            "chain_id": chain_id,
        }

    if category == "erc20":
        asset = str(raw.get("asset") or "").upper()
        if not asset:
            contract = normalize_evm_address(raw.get("rawContract", {}).get("address") if isinstance(raw.get("rawContract"), dict) else None)
            if contract:
                from .asset_mapping import ERC20_CONTRACT_TO_ASSET

                asset = ERC20_CONTRACT_TO_ASSET.get(chain_id, {}).get(contract, "")
        if not asset:
            return None
        raw_value = raw.get("rawContract", {}).get("value") if isinstance(raw.get("rawContract"), dict) else None
        if raw_value:
            from .evm_rpc_client import hex_to_int, atomic_to_decimal

            amount = atomic_to_decimal(hex_to_int(str(raw_value)), asset)
            amount_atomic = str(hex_to_int(str(raw_value)))
        else:
            amount = Decimal(str(raw.get("value") or "0"))
            if amount <= 0:
                return None
            from services.exchange.assets import ASSET_PRECISION

            amount_atomic = str(int(amount * (Decimal(10) ** ASSET_PRECISION.get(asset, 6))))

        contract = contract_for_asset(chain_id, asset)
        return {
            "asset": asset,
            "amount": amount,
            "amount_atomic": amount_atomic,
            "from_address": normalize_evm_address(raw.get("from")),
            "to_address": to_addr,
            "contract_address": contract,
            "tx_hash": tx_hash,
            "log_index": 0,
            "block_number": block_number,
            "chain_id": chain_id,
        }
    return None


def discover_missing_transfers_for_wallet(
    db: Session,
    *,
    chain_id: int,
    wallet_address: str,
) -> list[dict[str, Any]]:
    rpc_url = resolve_chain_rpc_url(chain_id)
    if not rpc_url:
        return []

    deposit_repo = PersonWalletDepositRepository()
    raw_transfers = fetch_alchemy_asset_transfers_to_wallet(rpc_url, wallet_address=wallet_address)
    missing: list[dict[str, Any]] = []

    for raw in raw_transfers:
        internal = alchemy_transfer_to_internal(raw, chain_id=chain_id, wallet_address=wallet_address)
        if not internal:
            continue
        existing = deposit_repo.find_by_chain_tx(
            db,
            chain_id=chain_id,
            tx_hash=str(internal["tx_hash"]).lower(),
            log_index=int(internal.get("log_index") or 0),
        )
        if existing:
            continue
        missing.append(internal)
    return missing


def fetch_aggregated_on_chain_balances(
    *,
    wallet_address: str,
    chain_ids: list[int],
    assets: list[str],
) -> dict[tuple[int, str], Decimal]:
    balances: dict[tuple[int, str], Decimal] = {}
    for chain_id in chain_ids:
        rpc_url = resolve_chain_rpc_url(chain_id)
        if not rpc_url:
            continue
        for asset in assets:
            try:
                balances[(chain_id, asset.upper())] = fetch_on_chain_asset_balance(
                    rpc_url,
                    chain_id=chain_id,
                    wallet_address=wallet_address,
                    asset=asset.upper(),
                )
            except EvmRpcError:
                balances[(chain_id, asset.upper())] = Decimal("0")
    return balances
