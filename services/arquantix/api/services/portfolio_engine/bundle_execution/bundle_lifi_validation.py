"""Validation des legs bundle sur Base (Phase 2)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from services.lifi.config import MAX_SLIPPAGE_BPS, default_slippage_bps

from .lifi_base_config import (
    BUNDLE_LIFI_CHAIN_KEY,
    BUNDLE_LIFI_DESTINATION_ASSETS,
    BUNDLE_LIFI_EXIT_DESTINATION_ASSETS,
    BUNDLE_LIFI_EXIT_SOURCE_ASSETS,
    BUNDLE_LIFI_SOURCE_ASSETS,
    DEFAULT_BUNDLE_EXIT_MIN,
    DEFAULT_BUNDLE_MIN,
    is_bundle_lifi_asset,
    normalize_bundle_asset,
    resolve_bundle_base_token,
    validate_bundle_exit_leg_assets,
    validate_bundle_leg_assets,
)

# BTC on-chain natif interdit — allocation logique BTC → token exécutable CBBTC (Base).
_FORBIDDEN_NATIVE_BTC_SOURCES = frozenset({"BTC", "WBTC", "TBTC"})


class BundleLifiValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def validate_bundle_lifi_leg(
    *,
    from_asset: str,
    to_asset: str,
    amount_from: Decimal,
    chain: str | None = None,
    leg_action: str | None = None,
) -> None:
    chain_key = (chain or BUNDLE_LIFI_CHAIN_KEY).strip().lower()
    if chain_key != BUNDLE_LIFI_CHAIN_KEY:
        raise BundleLifiValidationError(
            "bundle.lifi.chain_not_allowed",
            f"Bundles LI.FI limités à Base (reçu: {chain_key})",
        )
    try:
        if leg_action in ("withdraw_sell", "rebalance_sell"):
            validate_bundle_exit_leg_assets(from_asset, to_asset)
        else:
            validate_bundle_leg_assets(from_asset, to_asset)
    except ValueError as exc:
        raise BundleLifiValidationError("bundle.lifi.asset", str(exc)) from exc

    if amount_from <= 0:
        raise BundleLifiValidationError("bundle.lifi.amount", "Montant invalide")

    from_sym = normalize_bundle_asset(from_asset)
    minimum = (
        DEFAULT_BUNDLE_EXIT_MIN.get(from_sym, Decimal("0.00000001"))
        if leg_action in ("withdraw_sell", "rebalance_sell")
        else DEFAULT_BUNDLE_MIN.get(from_sym, Decimal("1"))
    )
    if amount_from < minimum:
        raise BundleLifiValidationError(
            "bundle.lifi.min_amount",
            f"Montant minimum {from_sym}: {minimum}",
        )


def _parse_bundle_human_amount(raw: str) -> Decimal:
    text = (raw or "").strip().replace(",", ".")
    if not text:
        raise BundleLifiValidationError("bundle.lifi.amount", "Montant requis")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise BundleLifiValidationError("bundle.lifi.amount", "Montant invalide") from exc
    if amount <= 0:
        raise BundleLifiValidationError("bundle.lifi.amount", "Montant doit être positif")
    return amount


def _validate_bundle_slippage_bps(slippage_bps: int | None) -> int:
    value = default_slippage_bps() if slippage_bps is None else int(slippage_bps)
    if value < 1 or value > MAX_SLIPPAGE_BPS:
        raise BundleLifiValidationError(
            "bundle.lifi.slippage",
            f"Slippage max {MAX_SLIPPAGE_BPS} bps",
        )
    return value


def validate_bundle_quote_request(
    *,
    from_asset: str,
    to_asset: str,
    amount: str,
    slippage_bps: int | None = None,
) -> tuple[Decimal, int]:
    """Validation quote bundle — whitelist ``lifi_base_config`` uniquement (pas portail V1)."""
    from_raw = (from_asset or "").strip().upper()
    to_raw = (to_asset or "").strip().upper()

    if from_raw in _FORBIDDEN_NATIVE_BTC_SOURCES:
        raise BundleLifiValidationError(
            "bundle.lifi.native_btc_forbidden",
            "BTC natif non autorisé en entrée bundle LI.FI — utiliser USDC ou EURC",
        )

    from_sym = normalize_bundle_asset(from_asset)
    to_sym = normalize_bundle_asset(to_asset)

    if to_raw == "BTC" and to_sym != "CBBTC":
        raise BundleLifiValidationError(
            "bundle.lifi.btc_must_map_cbbtc",
            "Allocation BTC doit s'exécuter en CBBTC sur Base",
        )

    validate_bundle_lifi_leg(
        from_asset=from_sym,
        to_asset=to_sym,
        amount_from=max(Decimal("1"), DEFAULT_BUNDLE_MIN.get(from_sym, Decimal("1"))),
        chain=BUNDLE_LIFI_CHAIN_KEY,
    )

    if from_sym not in BUNDLE_LIFI_SOURCE_ASSETS:
        raise BundleLifiValidationError(
            "bundle.lifi.source_not_allowed",
            f"Source bundle non autorisée: {from_sym}",
        )
    if to_sym not in BUNDLE_LIFI_DESTINATION_ASSETS:
        raise BundleLifiValidationError(
            "bundle.lifi.destination_not_allowed",
            f"Destination bundle non autorisée: {to_sym}",
        )

    if not is_bundle_lifi_asset(from_sym) or not is_bundle_lifi_asset(to_sym):
        raise BundleLifiValidationError("bundle.lifi.asset", "Actif non autorisé (bundle Base)")

    parsed_amount = _parse_bundle_human_amount(amount)
    minimum = DEFAULT_BUNDLE_MIN.get(from_sym, Decimal("1"))
    if parsed_amount < minimum:
        raise BundleLifiValidationError(
            "bundle.lifi.min_amount",
            f"Montant minimum {from_sym}: {minimum}",
        )

    resolve_bundle_base_token(from_sym)
    resolve_bundle_base_token(to_sym)

    slippage = _validate_bundle_slippage_bps(slippage_bps)
    return parsed_amount, slippage


def validate_bundle_exit_quote_request(
    *,
    from_asset: str,
    to_asset: str,
    amount: str,
    slippage_bps: int | None = None,
) -> tuple[Decimal, int]:
    """Validation quote bundle exit — spot → USDC/EURC (retrait / rebalance sell)."""
    from_sym = normalize_bundle_asset(from_asset)
    to_sym = normalize_bundle_asset(to_asset)

    parsed_amount = _parse_bundle_human_amount(amount)
    validate_bundle_lifi_leg(
        from_asset=from_sym,
        to_asset=to_sym,
        amount_from=parsed_amount,
        chain=BUNDLE_LIFI_CHAIN_KEY,
        leg_action="withdraw_sell",
    )

    if from_sym not in BUNDLE_LIFI_EXIT_SOURCE_ASSETS:
        raise BundleLifiValidationError(
            "bundle.lifi.exit_source_not_allowed",
            f"Source exit bundle non autorisée: {from_sym}",
        )
    if to_sym not in BUNDLE_LIFI_EXIT_DESTINATION_ASSETS:
        raise BundleLifiValidationError(
            "bundle.lifi.exit_destination_not_allowed",
            f"Destination exit bundle non autorisée: {to_sym}",
        )

    if not is_bundle_lifi_asset(from_sym) or not is_bundle_lifi_asset(to_sym):
        raise BundleLifiValidationError("bundle.lifi.asset", "Actif non autorisé (bundle Base)")

    minimum = DEFAULT_BUNDLE_EXIT_MIN.get(from_sym, Decimal("0.00000001"))
    if parsed_amount < minimum:
        raise BundleLifiValidationError(
            "bundle.lifi.min_amount",
            f"Montant minimum {from_sym}: {minimum}",
        )

    resolve_bundle_base_token(from_sym)
    resolve_bundle_base_token(to_sym)

    slippage = _validate_bundle_slippage_bps(slippage_bps)
    return parsed_amount, slippage
