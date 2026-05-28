"""Replay eth_getLogs ERC20 Transfer sur une plage de blocs (Base pilote)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from services.privy_wallet.asset_mapping import ERC20_CONTRACT_TO_ASSET, normalize_evm_address
from services.privy_wallet.evm_chain_config import is_alchemy_rpc, resolve_chain_rpc_url
from services.privy_wallet.evm_rpc_client import TRANSFER_TOPIC, hex_to_int, json_rpc_call

from database import PersonCryptoWallet
from .repository import RawOnChainEventRepository

logger = logging.getLogger(__name__)

DEFAULT_BLOCK_CHUNK = 2_000
ALCHEMY_FREE_MAX_BLOCK_CHUNK = 10
MAX_BLOCK_RANGE = 50_000


@dataclass
class BlockRangeReplayResult:
    chain_id: int
    from_block: int
    to_block: int
    dry_run: bool
    wallets_monitored: int = 0
    contracts_scanned: int = 0
    logs_scanned: int = 0
    events_prepared: int = 0
    events_inserted: int = 0
    events_skipped_existing: int = 0
    preview: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "from_block": self.from_block,
            "to_block": self.to_block,
            "dry_run": self.dry_run,
            "wallets_monitored": self.wallets_monitored,
            "contracts_scanned": self.contracts_scanned,
            "logs_scanned": self.logs_scanned,
            "events_prepared": self.events_prepared,
            "events_inserted": self.events_inserted,
            "events_skipped_existing": self.events_skipped_existing,
            "preview": self.preview[:50],
            "preview_truncated": len(self.preview) > 50,
            "errors": self.errors,
        }


def load_monitored_wallet_addresses(db: Session, *, chain_id: int) -> set[str]:
    rows = (
        db.query(PersonCryptoWallet)
        .filter(
            PersonCryptoWallet.revoked_at.is_(None),
            PersonCryptoWallet.chain_id.in_([chain_id, None]),
        )
        .all()
    )
    out: set[str] = set()
    for row in rows:
        addr = normalize_evm_address(row.address)
        if addr:
            out.add(addr.lower())
    return out


def _parse_transfer_log(
    log: dict[str, Any],
    *,
    chain_id: int,
    contract_to_asset: dict[str, str],
    monitored_wallets: set[str],
) -> dict[str, Any] | None:
    topics = log.get("topics") or []
    if len(topics) < 3:
        return None
    if str(topics[0]).lower() != TRANSFER_TOPIC:
        return None

    contract = normalize_evm_address(log.get("address"))
    if not contract:
        return None
    asset = contract_to_asset.get(contract.lower())
    if not asset:
        return None

    to_addr = normalize_evm_address("0x" + str(topics[2])[-40:])
    if not to_addr or to_addr.lower() not in monitored_wallets:
        return None

    from_addr = normalize_evm_address("0x" + str(topics[1])[-40:])
    amount_atomic = hex_to_int(log.get("data"))
    if amount_atomic <= 0:
        return None

    tx_hash = str(log.get("transactionHash") or "").lower()
    block_number = hex_to_int(log.get("blockNumber"))
    log_index = hex_to_int(log.get("logIndex"))

    transfer = {
        "asset": asset,
        "amount_atomic": str(amount_atomic),
        "from_address": from_addr,
        "to_address": to_addr,
        "contract_address": contract,
        "tx_hash": tx_hash,
        "log_index": log_index,
        "block_number": block_number,
        "chain_id": chain_id,
    }

    return {
        "chain_id": chain_id,
        "block_number": block_number,
        "tx_hash": tx_hash,
        "log_index": log_index,
        "contract_address": contract,
        "event_type": "erc20_transfer",
        "wallet_address": to_addr.lower(),
        "asset": asset,
        "amount_raw": amount_atomic,
        "payload_json": {
            "transfer": transfer,
            "source": "block_range_replay",
        },
    }


def _wallet_transfer_topic(wallet_address: str) -> str:
    addr = (wallet_address or "").lower().replace("0x", "")
    return "0x" + addr.rjust(64, "0")


def _fetch_transfer_logs(
    rpc_url: str,
    *,
    contract: str,
    from_block: int,
    to_block: int,
    to_wallet: str | None = None,
) -> list[dict[str, Any]]:
    topics: list[Any] = [TRANSFER_TOPIC]
    if to_wallet:
        topics.extend([None, _wallet_transfer_topic(to_wallet)])
    params = [
        {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
            "address": contract,
            "topics": topics,
        }
    ]
    result = json_rpc_call(rpc_url, "eth_getLogs", params, timeout=60.0)
    if not isinstance(result, list):
        return []
    return [log for log in result if isinstance(log, dict)]


def effective_block_chunk(rpc_url: str, requested: int) -> int:
    """Alchemy Free : eth_getLogs limité à 10 blocs par requête."""
    if is_alchemy_rpc(rpc_url):
        return min(max(requested, 1), ALCHEMY_FREE_MAX_BLOCK_CHUNK)
    return max(requested, 1)


def replay_block_range(
    db: Session,
    *,
    chain_id: int,
    from_block: int,
    to_block: int,
    dry_run: bool = True,
    block_chunk: int = DEFAULT_BLOCK_CHUNK,
    wallet_addresses: set[str] | None = None,
    assets: list[str] | None = None,
) -> BlockRangeReplayResult:
    if from_block < 0 or to_block < from_block:
        raise ValueError("Plage de blocs invalide")
    if to_block - from_block > MAX_BLOCK_RANGE:
        raise ValueError(f"Plage max {MAX_BLOCK_RANGE} blocs par exécution")

    rpc_url = resolve_chain_rpc_url(chain_id)
    if not rpc_url:
        raise ValueError(f"RPC non configuré pour chain_id={chain_id}")

    block_chunk = effective_block_chunk(rpc_url, block_chunk)

    if wallet_addresses:
        monitored = {
            (normalize_evm_address(a) or a).lower()
            for a in wallet_addresses
            if normalize_evm_address(a) or a
        }
    else:
        monitored = load_monitored_wallet_addresses(db, chain_id=chain_id)

    contract_map = ERC20_CONTRACT_TO_ASSET.get(chain_id, {})
    if assets:
        wanted = {a.strip().upper() for a in assets if a.strip()}
        contracts = [
            addr
            for addr, sym in contract_map.items()
            if sym.upper() in wanted
        ]
    else:
        contracts = list(contract_map.keys())

    result = BlockRangeReplayResult(
        chain_id=chain_id,
        from_block=from_block,
        to_block=to_block,
        dry_run=dry_run,
        wallets_monitored=len(monitored),
        contracts_scanned=len(contracts),
    )

    if not monitored:
        result.errors.append("Aucun wallet actif à surveiller pour cette chaîne.")
        return result

    for contract in contracts:
        for wallet in sorted(monitored):
            block_start = from_block
            while block_start <= to_block:
                block_end = min(block_start + block_chunk - 1, to_block)
                try:
                    logs = _fetch_transfer_logs(
                        rpc_url,
                        contract=contract,
                        from_block=block_start,
                        to_block=block_end,
                        to_wallet=wallet,
                    )
                except Exception as exc:
                    result.errors.append(
                        f"eth_getLogs {contract} → {wallet[:10]}… [{block_start}-{block_end}]: {exc}",
                    )
                    block_start = block_end + 1
                    continue

                result.logs_scanned += len(logs)

                for log in logs:
                    event_data = _parse_transfer_log(
                        log,
                        chain_id=chain_id,
                        contract_to_asset=contract_map,
                        monitored_wallets=monitored,
                    )
                    if event_data is None:
                        continue

                    result.events_prepared += 1
                    preview_item = {
                        "tx_hash": event_data["tx_hash"],
                        "log_index": event_data["log_index"],
                        "wallet_address": event_data["wallet_address"],
                        "asset": event_data["asset"],
                        "amount_raw": str(event_data["amount_raw"]),
                        "block_number": event_data["block_number"],
                    }
                    result.preview.append(preview_item)

                    if dry_run:
                        continue

                    _, created = RawOnChainEventRepository.insert_if_absent(db, data=event_data)
                    if created:
                        result.events_inserted += 1
                    else:
                        result.events_skipped_existing += 1

                block_start = block_end + 1

    return result
