"""Client JSON-RPC minimal pour soldes et receipts EVM (réconciliation Privy)."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any

from services.exchange.assets import ASSET_PRECISION

from .asset_mapping import ERC20_CONTRACT_TO_ASSET, contract_for_asset, normalize_evm_address
from .evm_chain_config import is_alchemy_rpc

logger = logging.getLogger(__name__)

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
_BALANCE_OF_SELECTOR = "0x70a08231"


class EvmRpcError(Exception):
    def __init__(self, message: str, *, code: str = "evm.rpc.error"):
        self.code = code
        super().__init__(message)


def json_rpc_call(rpc_url: str, method: str, params: list[Any], *, timeout: float = 20.0) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    req = urllib.request.Request(
        rpc_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise EvmRpcError(f"RPC HTTP {exc.code} ({method})", code="evm.rpc.http_error") from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise EvmRpcError(f"RPC indisponible ({method})", code="evm.rpc.unavailable") from exc

    if "error" in body:
        err = body["error"]
        message = err.get("message") if isinstance(err, dict) else str(err)
        raise EvmRpcError(message or f"RPC error ({method})", code="evm.rpc.response_error")
    return body.get("result")


def hex_to_int(value: str | None) -> int:
    if not value:
        return 0
    text = str(value).strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    return int(text or "0", 16)


def atomic_to_decimal(amount_atomic: int, asset: str) -> Decimal:
    precision = ASSET_PRECISION.get(asset.upper(), 18)
    return Decimal(amount_atomic) / (Decimal(10) ** precision)


def fetch_native_balance_wei(rpc_url: str, wallet_address: str) -> int:
    result = json_rpc_call(rpc_url, "eth_getBalance", [wallet_address, "latest"])
    return hex_to_int(result)


def fetch_erc20_balance_atomic(rpc_url: str, *, contract: str, wallet_address: str) -> int:
    addr = normalize_evm_address(wallet_address)
    if not addr:
        raise EvmRpcError("Adresse wallet invalide", code="evm.rpc.invalid_address")
    data = _BALANCE_OF_SELECTOR + addr[2:].rjust(64, "0")
    result = json_rpc_call(
        rpc_url,
        "eth_call",
        [{"to": contract, "data": data}, "latest"],
    )
    return hex_to_int(result)


def fetch_on_chain_asset_balance(
    rpc_url: str,
    *,
    chain_id: int,
    wallet_address: str,
    asset: str,
) -> Decimal:
    asset_u = asset.upper()
    contract = contract_for_asset(chain_id, asset_u)
    if contract:
        atomic = fetch_erc20_balance_atomic(rpc_url, contract=contract, wallet_address=wallet_address)
        return atomic_to_decimal(atomic, asset_u)
    if asset_u == "ETH":
        wei = fetch_native_balance_wei(rpc_url, wallet_address)
        return atomic_to_decimal(wei, "ETH")
    return Decimal("0")


def fetch_transaction_receipt(rpc_url: str, tx_hash: str) -> dict[str, Any]:
    result = json_rpc_call(rpc_url, "eth_getTransactionReceipt", [tx_hash])
    if not isinstance(result, dict):
        raise EvmRpcError("Receipt introuvable", code="evm.rpc.receipt_missing")
    return result


def fetch_transaction(rpc_url: str, tx_hash: str) -> dict[str, Any]:
    result = json_rpc_call(rpc_url, "eth_getTransactionByHash", [tx_hash])
    if not isinstance(result, dict):
        raise EvmRpcError("Transaction introuvable", code="evm.rpc.tx_missing")
    return result


def _topic_address(address: str) -> str:
    addr = normalize_evm_address(address) or ""
    return "0x" + addr[2:].rjust(64, "0")


def parse_erc20_transfers_from_receipt(
    receipt: dict[str, Any],
    *,
    chain_id: int,
    wallet_address: str,
) -> list[dict[str, Any]]:
    to_topic = _topic_address(wallet_address)
    contract_map = ERC20_CONTRACT_TO_ASSET.get(chain_id, {})
    out: list[dict[str, Any]] = []

    for log in receipt.get("logs") or []:
        if not isinstance(log, dict):
            continue
        topics = log.get("topics") or []
        if len(topics) < 3:
            continue
        if str(topics[0]).lower() != TRANSFER_TOPIC:
            continue
        if str(topics[2]).lower() != to_topic.lower():
            continue

        contract = normalize_evm_address(log.get("address"))
        if not contract:
            continue
        asset = contract_map.get(contract)
        if not asset:
            continue

        from_addr = "0x" + str(topics[1])[-40:]
        amount_atomic = hex_to_int(log.get("data"))
        if amount_atomic <= 0:
            continue

        out.append(
            {
                "asset": asset,
                "amount": atomic_to_decimal(amount_atomic, asset),
                "amount_atomic": str(amount_atomic),
                "from_address": normalize_evm_address(from_addr),
                "to_address": normalize_evm_address(wallet_address),
                "contract_address": contract,
                "tx_hash": str(receipt.get("transactionHash") or "").lower(),
                "log_index": hex_to_int(log.get("logIndex")),
                "block_number": hex_to_int(receipt.get("blockNumber")),
                "chain_id": chain_id,
            }
        )
    return out


def parse_native_transfer_from_tx(
    tx: dict[str, Any],
    *,
    chain_id: int,
    wallet_address: str,
) -> dict[str, Any] | None:
    to_addr = normalize_evm_address(tx.get("to"))
    if to_addr != normalize_evm_address(wallet_address):
        return None
    value_wei = hex_to_int(tx.get("value"))
    if value_wei <= 0:
        return None
    return {
        "asset": "ETH",
        "amount": atomic_to_decimal(value_wei, "ETH"),
        "amount_atomic": str(value_wei),
        "from_address": normalize_evm_address(tx.get("from")),
        "to_address": to_addr,
        "contract_address": None,
        "tx_hash": str(tx.get("hash") or "").lower(),
        "log_index": 0,
        "block_number": hex_to_int(tx.get("blockNumber")),
        "chain_id": chain_id,
    }


def fetch_alchemy_asset_transfers_to_wallet(
    rpc_url: str,
    *,
    wallet_address: str,
    from_block: str = "0x0",
    to_block: str = "latest",
) -> list[dict[str, Any]]:
    if not is_alchemy_rpc(rpc_url):
        return []

    params = {
        "fromBlock": from_block,
        "toBlock": to_block,
        "toAddress": normalize_evm_address(wallet_address),
        "category": ["erc20", "external"],
        "withMetadata": True,
        "excludeZeroValue": True,
        "maxCount": "0x3e8",
    }
    try:
        result = json_rpc_call(rpc_url, "alchemy_getAssetTransfers", [params], timeout=30.0)
    except EvmRpcError:
        logger.info("alchemy_getAssetTransfers unavailable", exc_info=True)
        return []

    transfers = result.get("transfers") if isinstance(result, dict) else None
    if not isinstance(transfers, list):
        return []
    return [t for t in transfers if isinstance(t, dict)]
