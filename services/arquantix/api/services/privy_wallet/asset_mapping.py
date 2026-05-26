"""Mapping actifs on-chain (CAIP-2, contrats ERC-20) → symboles ledger Privy."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from services.exchange.assets import ASSET_PRECISION, SUPPORTED_ASSETS

# Contrats ERC-20 par réseau — alignés watchlist Privy (ETH natif via NATIVE_SYMBOL_BY_CHAIN).
EVM_ERC20_CONTRACTS: dict[int, dict[str, str]] = {
    1: {
        "USDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "EURC": "0x1abaea1f781e1f27444163d08077255fb56359a",
        "USDT": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    },
    8453: {
        "USDC": "0x833589fCD6eDb6E08Ab4aB98b4690795417555",
        "EURC": "0x60a3E35Cc2b24469b62337c93687d29a08D49Aca",
    },
}

ERC20_CONTRACT_TO_ASSET: dict[int, dict[str, str]] = {
    chain_id: {contract.lower(): asset for asset, contract in contracts.items()}
    for chain_id, contracts in EVM_ERC20_CONTRACTS.items()
}

NATIVE_SYMBOL_BY_CHAIN: dict[int, str] = {
    1: "ETH",
    11155111: "ETH",  # Sepolia
    8453: "ETH",  # Base
    42161: "ETH",  # Arbitrum
    10: "ETH",  # Optimism
    137: "MATIC",
}

# Rétrocompat tests / imports historiques.
ETHEREUM_MAINNET_ERC20: dict[str, str] = EVM_ERC20_CONTRACTS[1]


def contract_for_asset(chain_id: int, asset: str) -> str | None:
    contracts = EVM_ERC20_CONTRACTS.get(chain_id, {})
    return contracts.get(asset.upper())


def supported_assets_for_chain(chain_id: int) -> list[str]:
    assets = set(EVM_ERC20_CONTRACTS.get(chain_id, {}).keys())
    if chain_id in NATIVE_SYMBOL_BY_CHAIN:
        assets.add(NATIVE_SYMBOL_BY_CHAIN[chain_id])
    return sorted(assets)


def parse_caip2_chain_id(raw: str | int | None) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if text.startswith("eip155:"):
        suffix = text.split(":", 1)[1]
        return int(suffix) if suffix.isdigit() else None
    return None


def normalize_evm_address(address: str | None) -> str | None:
    if address is None:
        return None
    addr = str(address).strip().lower()
    if not addr:
        return None
    if not addr.startswith("0x"):
        addr = f"0x{addr}"
    return addr


def resolve_asset_symbol(
    *,
    chain_id: int | None,
    asset_payload: dict | str | None,
    contract_address: str | None = None,
) -> str | None:
    """Résout le symbole canonique (ETH, USDC, …) depuis le payload Privy."""
    if isinstance(asset_payload, str) and asset_payload.strip():
        sym = asset_payload.strip().upper()
        if sym in SUPPORTED_ASSETS or sym in {"MATIC", "WETH"}:
            return "ETH" if sym == "WETH" else sym

    if isinstance(asset_payload, dict):
        sym = (
            asset_payload.get("symbol")
            or asset_payload.get("ticker")
            or asset_payload.get("name")
        )
        if sym:
            sym_u = str(sym).strip().upper()
            if sym_u == "WETH":
                return "ETH"
            if sym_u in SUPPORTED_ASSETS or sym_u == "MATIC":
                return sym_u

        asset_type = str(asset_payload.get("type") or asset_payload.get("asset_type") or "").lower()
        if asset_type in ("native", "native_token", "native-token"):
            if chain_id is not None:
                return NATIVE_SYMBOL_BY_CHAIN.get(chain_id, "ETH")
            return "ETH"

        contract = contract_address or asset_payload.get("contract_address") or asset_payload.get("address")
        if contract and chain_id is not None:
            mapped = ERC20_CONTRACT_TO_ASSET.get(chain_id, {}).get(normalize_evm_address(contract) or "")
            if mapped:
                return mapped

    if contract_address and chain_id is not None:
        mapped = ERC20_CONTRACT_TO_ASSET.get(chain_id, {}).get(normalize_evm_address(contract_address) or "")
        if mapped:
            return mapped

    return None


def parse_amount_to_decimal(amount_raw: object, asset: str) -> Decimal:
    """Convertit un montant Privy (souvent en unités atomiques) en Decimal lisible."""
    if amount_raw is None:
        raise ValueError("Missing amount")

    precision = ASSET_PRECISION.get(asset, 18)

    if isinstance(amount_raw, dict):
        raw = amount_raw.get("amount") or amount_raw.get("value") or amount_raw.get("raw")
        if raw is None:
            raise ValueError("Missing amount in amount object")
        return parse_amount_to_decimal(raw, asset)

    text = str(amount_raw).strip()
    if not text:
        raise ValueError("Empty amount")

    if "." in text or "e" in text.lower():
        try:
            return Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid decimal amount: {text}") from exc

    try:
        atomic = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid atomic amount: {text}") from exc

    divisor = Decimal(10) ** precision
    return atomic / divisor


def format_amount_display(amount: Decimal, asset: str) -> str:
    precision = ASSET_PRECISION.get(asset, 8)
    q = Decimal(10) ** -min(precision, 8)
    normalized = amount.quantize(q)
    text = format(normalized, "f").rstrip("0").rstrip(".")
    return text or "0"
