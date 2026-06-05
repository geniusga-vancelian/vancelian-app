"""Validation stricte des requêtes swap (whitelist, montants, slippage)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from config.supported_swap_assets import (
    DEFAULT_MAX_SWAP_AMOUNT,
    effective_min_swap_amount,
    SUPPORTED_SWAP_CHAINS,
    asset_available_on_chain,
    is_evm_swap_chain,
    is_supported_asset,
    is_supported_chain,
    is_swap_destination_asset,
    is_swap_source_asset,
    normalize_asset_symbol,
    normalize_chain_key,
    resolve_swap_token,
)
from services.lifi.config import MAX_SLIPPAGE_BPS, default_slippage_bps, swap_v1_same_chain_only


class SwapValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class SwapPriceChangedError(Exception):
    """Quote fraîche hors bande slippage vs snapshot Review."""

    def __init__(
        self,
        *,
        quote: "SwapQuoteResponse",
        delta_bps: int,
        slippage_bps: int,
        message: str | None = None,
    ):
        from services.lifi.schemas import SwapQuoteResponse

        self.code = "swap.price_changed"
        self.quote: SwapQuoteResponse = quote
        self.delta_bps = delta_bps
        self.slippage_bps = slippage_bps
        self.message = message or (
            "Le montant estimé à recevoir a légèrement changé. Vérifiez le récapitulatif avant de confirmer."
        )
        super().__init__(self.message)


def parse_human_amount(raw: str) -> Decimal:
    text = (raw or "").strip().replace(",", ".")
    if not text:
        raise SwapValidationError("swap.invalid_amount", "Montant requis")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise SwapValidationError("swap.invalid_amount", "Montant invalide") from exc
    if amount <= 0:
        raise SwapValidationError("swap.invalid_amount", "Montant doit être positif")
    return amount


def validate_slippage_bps(slippage_bps: int | None) -> int:
    value = default_slippage_bps() if slippage_bps is None else int(slippage_bps)
    if value < 1 or value > MAX_SLIPPAGE_BPS:
        raise SwapValidationError(
            "swap.invalid_slippage",
            f"Slippage max {MAX_SLIPPAGE_BPS} bps (1%)",
        )
    return value


def validate_quote_request(
    *,
    from_asset: str,
    to_asset: str,
    amount: str,
    from_chain: str,
    to_chain: str,
    slippage_bps: int | None = None,
) -> tuple[Decimal, int]:
    from_sym = normalize_asset_symbol(from_asset)
    to_sym = normalize_asset_symbol(to_asset)
    from_chain_key = normalize_chain_key(from_chain)
    to_chain_key = normalize_chain_key(to_chain)

    if from_sym == to_sym and from_chain_key == to_chain_key:
        raise SwapValidationError("swap.same_asset", "Source et destination identiques")

    if not is_supported_asset(from_sym) or not is_supported_asset(to_sym):
        raise SwapValidationError("swap.asset_not_whitelisted", "Actif non autorisé")

    if not is_swap_source_asset(from_sym):
        raise SwapValidationError(
            "swap.source_not_allowed",
            "Actif source non autorisé (V1 : USDC, USDT, ETH — EVM uniquement)",
        )

    if not is_swap_destination_asset(to_sym):
        raise SwapValidationError(
            "swap.destination_not_allowed",
            "Destination non autorisée (V1 : USDC, USDT, ETH — EVM uniquement)",
        )

    if not is_supported_chain(from_chain_key) or not is_supported_chain(to_chain_key):
        raise SwapValidationError("swap.chain_not_supported", "Chaîne non supportée")

    if not is_evm_swap_chain(from_chain_key) or not is_evm_swap_chain(to_chain_key):
        raise SwapValidationError(
            "swap.chain_not_evm",
            "Swaps V1 limités aux chaînes EVM",
        )

    if swap_v1_same_chain_only() and from_chain_key != to_chain_key:
        raise SwapValidationError(
            "swap.cross_chain_disabled",
            "Swaps cross-chain désactivés en V1 — source et destination doivent être sur la même chaîne (pilote : Ethereum)",
        )

    if not asset_available_on_chain(from_sym, from_chain_key):
        raise SwapValidationError(
            "swap.asset_unavailable_on_chain",
            f"{from_sym} indisponible sur {from_chain_key}",
        )
    if not asset_available_on_chain(to_sym, to_chain_key):
        raise SwapValidationError(
            "swap.asset_unavailable_on_chain",
            f"{to_sym} indisponible sur {to_chain_key}",
        )

    parsed_amount = parse_human_amount(amount)
    min_amount = effective_min_swap_amount(from_sym)
    max_amount = DEFAULT_MAX_SWAP_AMOUNT.get(from_sym, Decimal("100000"))
    if parsed_amount < min_amount:
        raise SwapValidationError(
            "swap.amount_below_min",
            f"Montant minimum : {min_amount} {from_sym}",
        )
    if parsed_amount > max_amount:
        raise SwapValidationError(
            "swap.amount_above_max",
            f"Montant maximum : {max_amount} {from_sym}",
        )

    slippage = validate_slippage_bps(slippage_bps)

    # Résolution tokens — lève si adresse manquante.
    resolve_swap_token(from_sym, from_chain_key)
    resolve_swap_token(to_sym, to_chain_key)

    return parsed_amount, slippage


def wallet_chain_type_for_chain(chain_key: str) -> str:
    meta = SUPPORTED_SWAP_CHAINS[normalize_chain_key(chain_key)]
    return str(meta["wallet_chain_type"])
