"""Résolution du montant réellement reçu après swap LI.FI (on-chain > status API > mock dev)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from config.supported_swap_assets import SUPPORTED_SWAP_ASSETS, SUPPORTED_SWAP_CHAINS, atomic_amount_to_human, normalize_chain_key
from database import PersonCryptoWallet
from services.lifi.lifi_validation_service import SwapValidationError
from services.lifi.signing_wallet_service import read_signing_wallet_from_audit
from services.privy_wallet.asset_mapping import normalize_evm_address
from services.privy_wallet.repository import PersonCryptoWalletRepository
from services.privy_wallet.asset_mapping import NATIVE_SYMBOL_BY_CHAIN
from services.privy_wallet.evm_chain_config import resolve_chain_rpc_url
from services.privy_wallet.evm_rpc_client import (
    EvmRpcError,
    fetch_transaction,
    fetch_transaction_receipt,
    parse_erc20_transfers_from_receipt,
    parse_native_transfer_from_tx,
)

logger = logging.getLogger(__name__)

LIFI_SUBSTATUS_PARTIAL = "PARTIAL"
LIFI_SUBSTATUS_COMPLETED = "COMPLETED"


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


@dataclass(frozen=True)
class LifiActualReceiveResult:
    amount: Decimal
    source: str
    receive_tx_hash: str | None = None
    log_index: int | None = None


def _to_asset_decimals(to_asset: str) -> int:
    meta = SUPPORTED_SWAP_ASSETS.get(str(to_asset).upper(), {})
    return int(meta.get("decimals") or 18)


def _receive_tx_hash_from_status(swap, lifi_status_payload: dict[str, Any] | None) -> str:
    receiving = (lifi_status_payload or {}).get("receiving") or {}
    if isinstance(receiving, dict):
        raw = receiving.get("txHash") or receiving.get("tx_hash")
        if raw:
            return str(raw).strip().lower()
    return str(swap.tx_hash or "").strip().lower()


def _amount_from_on_chain_receive(
    db: Session,
    swap,
    *,
    lifi_status_payload: dict[str, Any] | None,
) -> LifiActualReceiveResult | None:
    tx_hash = _receive_tx_hash_from_status(swap, lifi_status_payload)
    if not tx_hash or not tx_hash.startswith("0x"):
        return None

    to_asset = str(swap.to_asset).upper()
    to_chain_id = _chain_id_for_swap(str(swap.to_chain))

    try:
        wallet = _resolve_swap_wallet(db, swap)
    except Exception:
        return None

    rpc_url = resolve_chain_rpc_url(to_chain_id)
    if not rpc_url:
        return None

    wallet_address = wallet.address
    if not wallet_address:
        return None

    try:
        if to_asset == (NATIVE_SYMBOL_BY_CHAIN.get(to_chain_id) or "ETH").upper():
            tx = fetch_transaction(rpc_url, tx_hash)
            native = parse_native_transfer_from_tx(
                tx,
                chain_id=to_chain_id,
                wallet_address=wallet_address,
            )
            if native and str(native.get("asset", "")).upper() == to_asset:
                amount = Decimal(str(native["amount"]))
                if amount > 0:
                    return LifiActualReceiveResult(
                        amount=amount,
                        source="on_chain_native_transfer",
                        receive_tx_hash=tx_hash,
                        log_index=int(native.get("log_index") or 0),
                    )

        receipt = fetch_transaction_receipt(rpc_url, tx_hash)
        transfers = parse_erc20_transfers_from_receipt(
            receipt,
            chain_id=to_chain_id,
            wallet_address=wallet_address,
        )
        matching = [t for t in transfers if str(t.get("asset", "")).upper() == to_asset]
        if not matching:
            return None

        total = Decimal("0")
        best = matching[0]
        for row in matching:
            total += Decimal(str(row["amount"]))
            if Decimal(str(row["amount"])) >= Decimal(str(best["amount"])):
                best = row

        if total <= 0:
            return None

        return LifiActualReceiveResult(
            amount=total,
            source="on_chain_erc20_transfer",
            receive_tx_hash=str(best.get("tx_hash") or tx_hash).lower(),
            log_index=int(best.get("log_index") or 0),
        )
    except EvmRpcError as exc:
        logger.warning(
            "lifi.actual_receive.on_chain_failed",
            extra={"swap_id": str(swap.id), "tx_hash": tx_hash, "code": exc.code},
        )
        return None
    except Exception:
        logger.warning("lifi.actual_receive.on_chain_failed", exc_info=True, extra={"swap_id": str(swap.id)})
        return None


def _amount_from_lifi_status_payload(
    lifi_status_payload: dict[str, Any],
    *,
    to_asset: str,
) -> LifiActualReceiveResult | None:
    receiving = lifi_status_payload.get("receiving")
    if not isinstance(receiving, dict):
        return None

    amount_atomic = receiving.get("amount")
    if amount_atomic is None or str(amount_atomic).strip() in {"", "0"}:
        return None

    token = receiving.get("token") if isinstance(receiving.get("token"), dict) else {}
    token_symbol = str(token.get("symbol") or "").strip().upper()
    asset_u = to_asset.upper()
    if token_symbol and token_symbol != asset_u:
        logger.info(
            "lifi.actual_receive.token_symbol_mismatch",
            extra={"expected": asset_u, "received": token_symbol},
        )
        return None

    decimals = int(token.get("decimals") or _to_asset_decimals(asset_u))
    amount = atomic_amount_to_human(str(amount_atomic), decimals)
    if amount <= 0:
        return None

    receive_tx = receiving.get("txHash") or receiving.get("tx_hash")
    return LifiActualReceiveResult(
        amount=amount,
        source="lifi_status_receiving",
        receive_tx_hash=str(receive_tx).strip().lower() if receive_tx else None,
    )


def _amount_from_mock_quote(swap) -> LifiActualReceiveResult | None:
    estimated = Decimal(str(swap.estimated_receive or 0))
    if estimated <= 0:
        return None
    return LifiActualReceiveResult(
        amount=estimated,
        source="lifi_mock_quote",
        receive_tx_hash=str(swap.tx_hash or "").strip().lower() or None,
    )


def resolve_lifi_actual_receive_amount(
    db: Session,
    swap,
    *,
    lifi_status_payload: dict[str, Any] | None = None,
    allow_mock_quote_amount: bool = False,
) -> LifiActualReceiveResult | None:
    """
    Détermine le montant réellement reçu (destination).

    Priorité : on-chain Transfer → LI.FI ``receiving.amount`` → quote mock (dev uniquement).
    """
    on_chain = _amount_from_on_chain_receive(db, swap, lifi_status_payload=lifi_status_payload)
    if on_chain is not None:
        return on_chain

    if lifi_status_payload:
        from_status = _amount_from_lifi_status_payload(
            lifi_status_payload,
            to_asset=str(swap.to_asset),
        )
        if from_status is not None:
            return from_status

    if allow_mock_quote_amount:
        return _amount_from_mock_quote(swap)

    return None


def is_lifi_done_complete_substatus(substatus: str) -> bool:
    normalized = (substatus or "").strip().upper()
    return normalized in {"", LIFI_SUBSTATUS_COMPLETED}


def is_lifi_partial_substatus(substatus: str) -> bool:
    return (substatus or "").strip().upper() == LIFI_SUBSTATUS_PARTIAL
