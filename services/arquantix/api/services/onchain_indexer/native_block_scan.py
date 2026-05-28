"""Scan ETH natif entrant par blocs (wallets connus uniquement)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from services.privy_wallet.asset_mapping import normalize_evm_address
from services.privy_wallet.evm_rpc_client import (
    fetch_block_by_number,
    parse_native_transfer_from_tx,
)

from .repository import RawOnChainEventRepository

logger = logging.getLogger(__name__)


@dataclass
class NativeBlockScanResult:
    from_block: int
    to_block: int
    dry_run: bool
    blocks_scanned: int = 0
    txs_scanned: int = 0
    events_prepared: int = 0
    events_inserted: int = 0
    events_skipped_existing: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_block": self.from_block,
            "to_block": self.to_block,
            "dry_run": self.dry_run,
            "blocks_scanned": self.blocks_scanned,
            "txs_scanned": self.txs_scanned,
            "events_prepared": self.events_prepared,
            "events_inserted": self.events_inserted,
            "events_skipped_existing": self.events_skipped_existing,
            "errors": self.errors,
        }


def scan_native_incoming_transfers(
    db: Session,
    *,
    chain_id: int,
    rpc_url: str,
    from_block: int,
    to_block: int,
    monitored_wallets: set[str],
    dry_run: bool = True,
) -> NativeBlockScanResult:
    result = NativeBlockScanResult(
        from_block=from_block,
        to_block=to_block,
        dry_run=dry_run,
    )
    if not monitored_wallets:
        return result

    for block_num in range(from_block, to_block + 1):
        try:
            block = fetch_block_by_number(rpc_url, block_num, full_txs=True)
        except Exception as exc:
            result.errors.append(f"eth_getBlockByNumber {block_num}: {exc}")
            return result

        result.blocks_scanned += 1
        txs = block.get("transactions") or []
        if not isinstance(txs, list):
            continue

        for tx in txs:
            if not isinstance(tx, dict):
                continue
            result.txs_scanned += 1
            to_addr = normalize_evm_address(tx.get("to"))
            if not to_addr or to_addr.lower() not in monitored_wallets:
                continue

            transfer = parse_native_transfer_from_tx(
                tx,
                chain_id=chain_id,
                wallet_address=to_addr,
            )
            if transfer is None:
                continue

            event_data = {
                "chain_id": chain_id,
                "block_number": transfer.get("block_number") or block_num,
                "tx_hash": transfer["tx_hash"],
                "log_index": int(transfer.get("log_index") or 0),
                "contract_address": None,
                "event_type": "native_transfer",
                "wallet_address": to_addr.lower(),
                "asset": "ETH",
                "amount_raw": int(transfer["amount_atomic"]),
                "payload_json": {
                    "transfer": transfer,
                    "source": "native_block_scan",
                },
            }
            result.events_prepared += 1

            if dry_run:
                continue

            _, created = RawOnChainEventRepository.insert_if_absent(db, data=event_data)
            if created:
                result.events_inserted += 1
            else:
                result.events_skipped_existing += 1

    return result
