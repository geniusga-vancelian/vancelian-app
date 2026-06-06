"""Portfolio breakdown par actif — lecture seule (Privy Ledger → PE → API → UI).

``total_holdings`` est **dérivé** des scopes métier additifs (available + in_vaults +
locked_collateral). Il ne doit pas être utilisé comme source de vérité opérationnelle
ni recopié tel quel depuis le ledger Privy.

WARNING — Les champs breakdown ne sont pas forcément additifs. Certaines composantes
représentent des sous-scopes économiques du wallet (allocations bundle notamment).
Le breakdown est explicatif, pas comptable.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from config.base_allowed_assets import BASE_LIFI_CHAIN_ID
from services.exchange.assets import ASSET_PRECISION
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.internal_scope_movements.pe_reader import read_current_pe_scope_snapshot
from services.portfolio_engine.internal_scope_movements.types import CurrentPeScopeSnapshot
from services.privy_wallet.deposit_backfill import fetch_aggregated_on_chain_balances
from services.privy_wallet.evm_chain_config import supported_pilot_chain_ids
from services.privy_wallet.repository import PersonCryptoWalletRepository, PersonWalletBalanceRepository

BREAKDOWN_VERSION = "portfolio_breakdown_v1"
CUSTODY_CHAIN_ID = BASE_LIFI_CHAIN_ID

_PENDING_SWAP_STATUSES = frozenset(
    {
        SwapSessionStatus.PENDING.value,
        SwapSessionStatus.QUOTE_RECEIVED.value,
        SwapSessionStatus.AWAITING_SIGNATURE.value,
        SwapSessionStatus.SUBMITTED.value,
    }
)

_COMPONENT_SCOPES: dict[str, dict[str, Any]] = {
    "available": {
        "economic_scope": "wallet_liquid_trading",
        "ownership_scope": "pe_trading_available",
        "additive": True,
    },
    "in_vaults": {
        "economic_scope": "wallet_vault_allocated",
        "ownership_scope": "pe_vault_position",
        "additive": True,
    },
    "in_bundles": {
        "economic_scope": "bundle_subset_of_wallet",
        "ownership_scope": "pe_bundle_allocation",
        "additive": False,
        "bundle_is_subset_of_wallet": True,
    },
    "locked_collateral": {
        "economic_scope": "lombard_collateral_locked",
        "ownership_scope": "pe_trading_locked_collateral",
        "additive": True,
    },
    "debt": {
        "economic_scope": "lombard_liability",
        "ownership_scope": "pe_liability",
        "additive": False,
    },
    "pending_settlement": {
        "economic_scope": "swap_in_flight",
        "ownership_scope": "lifi_pending_session",
        "additive": False,
    },
}


def _fmt(value: Decimal | None, *, asset: str) -> str:
    if value is None:
        qty = Decimal("0")
    else:
        qty = Decimal(str(value))
    precision = ASSET_PRECISION.get(asset.upper(), 8)
    text = f"{qty:.{precision}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _ledger_balances(db: Session, person_id: UUID) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for row in PersonWalletBalanceRepository.list_for_person(db, person_id):
        asset = str(row.asset).upper()
        out[asset] = out.get(asset, Decimal("0")) + Decimal(str(row.balance or 0))
    return out


def _pick_privy_embedded_wallet(db: Session, person_id: UUID):
    wallets = PersonCryptoWalletRepository.list_active_for_person(db, person_id)
    embedded = [w for w in wallets if (w.provider or "").lower() == "privy" and (w.wallet_type or "").lower() != "external"]
    if embedded:
        return embedded[0]
    privy = [w for w in wallets if (w.provider or "").lower() == "privy"]
    if privy:
        return privy[0]
    return wallets[0] if wallets else None


def _on_chain_base_balances(
    db: Session,
    person_id: UUID,
    ledger: dict[str, Decimal],
) -> dict[str, Decimal]:
    wallet = _pick_privy_embedded_wallet(db, person_id)
    if not wallet or not wallet.address:
        return {}
    assets = sorted(set(ledger.keys()))
    if not assets:
        return {}
    chain_ids = supported_pilot_chain_ids() or [CUSTODY_CHAIN_ID]
    try:
        raw = fetch_aggregated_on_chain_balances(
            wallet_address=wallet.address,
            chain_ids=chain_ids,
            assets=assets,
        )
    except Exception:
        return {}
    out: dict[str, Decimal] = {}
    for (cid, asset), bal in raw.items():
        if int(cid) == CUSTODY_CHAIN_ID:
            out[asset] = out.get(asset, Decimal("0")) + bal
    return out


def _pending_settlement_by_asset(db: Session, person_id: UUID) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    swaps = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == person_id,
            PersonWalletSwap.status.in_(sorted(_PENDING_SWAP_STATUSES)),
        )
        .all()
    )
    for swap in swaps:
        asset = str(swap.from_asset or "").upper()
        if not asset:
            continue
        out[asset] = out.get(asset, Decimal("0")) + Decimal(str(swap.amount_in or 0))
    return out


def _component_payload(asset: str, field: str, quantity: Decimal) -> dict[str, Any]:
    meta = dict(_COMPONENT_SCOPES[field])
    meta["quantity"] = _fmt(quantity, asset=asset)
    return meta


def build_asset_breakdown_row(
    asset: str,
    *,
    pe: CurrentPeScopeSnapshot,
    ledger: dict[str, Decimal],
    on_chain_base: dict[str, Decimal],
    pending_by_asset: dict[str, Decimal],
) -> dict[str, Any]:
    """Construit une ligne breakdown pour un actif (scopes PE = source métier)."""
    available = pe.trading_available.get(asset, Decimal("0"))
    in_vaults = pe.vault_position.get(asset, Decimal("0"))
    in_bundles = pe.bundle_cash.get(asset, Decimal("0")) + pe.bundle_position.get(asset, Decimal("0"))
    locked_collateral = pe.trading_locked_collateral.get(asset, Decimal("0"))
    debt = pe.liability.get(asset, Decimal("0"))
    pending_settlement = pending_by_asset.get(asset, Decimal("0"))

    total_holdings = available + in_vaults + locked_collateral

    wallet_ledger_balance = ledger.get(asset, Decimal("0"))
    on_chain_balance_base = on_chain_base.get(asset, Decimal("0"))
    ledger_spendable = max(wallet_ledger_balance - locked_collateral, Decimal("0"))
    if on_chain_balance_base > 0:
        swappable_balance = min(on_chain_balance_base, ledger_spendable)
    else:
        swappable_balance = ledger_spendable

    components_sum_including_bundles = available + in_vaults + in_bundles + locked_collateral
    non_additive_overlap = components_sum_including_bundles - total_holdings

    return {
        "symbol": asset,
        "total_holdings": _fmt(total_holdings, asset=asset),
        "available": _fmt(available, asset=asset),
        "in_vaults": _fmt(in_vaults, asset=asset),
        "in_bundles": _fmt(in_bundles, asset=asset),
        "locked_collateral": _fmt(locked_collateral, asset=asset),
        "debt": _fmt(debt, asset=asset),
        "pending_settlement": _fmt(pending_settlement, asset=asset),
        "swappable_balance": _fmt(swappable_balance, asset=asset),
        "wallet_ledger_balance": _fmt(wallet_ledger_balance, asset=asset),
        "on_chain_balance_base": _fmt(on_chain_balance_base, asset=asset),
        "components": {
            "available": _component_payload(asset, "available", available),
            "in_vaults": _component_payload(asset, "in_vaults", in_vaults),
            "in_bundles": _component_payload(asset, "in_bundles", in_bundles),
            "locked_collateral": _component_payload(asset, "locked_collateral", locked_collateral),
            "debt": _component_payload(asset, "debt", debt),
            "pending_settlement": _component_payload(asset, "pending_settlement", pending_settlement),
        },
        "bundle_is_subset_of_wallet": in_bundles > 0,
        "non_additive_overlap": _fmt(max(non_additive_overlap, Decimal("0")), asset=asset),
    }


def build_portfolio_breakdown(db: Session, person_id: UUID) -> dict[str, Any]:
    """Agrège le breakdown par actif pour une personne (lecture seule)."""
    pe = read_current_pe_scope_snapshot(db, person_id)
    ledger = _ledger_balances(db, person_id)
    on_chain_base = _on_chain_base_balances(db, person_id, ledger)
    pending_by_asset = _pending_settlement_by_asset(db, person_id)

    all_assets = sorted(
        set(pe.trading_available.keys())
        | set(pe.vault_position.keys())
        | set(pe.bundle_cash.keys())
        | set(pe.bundle_position.keys())
        | set(pe.trading_locked_collateral.keys())
        | set(pe.liability.keys())
        | set(ledger.keys())
        | set(on_chain_base.keys())
        | set(pending_by_asset.keys())
    )

    assets: list[dict[str, Any]] = []
    for asset in all_assets:
        row = build_asset_breakdown_row(
            asset,
            pe=pe,
            ledger=ledger,
            on_chain_base=on_chain_base,
            pending_by_asset=pending_by_asset,
        )
        if all(
            Decimal(str(row.get(k) or "0")) == 0
            for k in (
                "total_holdings",
                "available",
                "in_vaults",
                "in_bundles",
                "locked_collateral",
                "debt",
                "pending_settlement",
                "wallet_ledger_balance",
            )
        ):
            continue
        assets.append(row)

    swappable_by_asset = {row["symbol"]: row["swappable_balance"] for row in assets}

    return {
        "breakdown_version": BREAKDOWN_VERSION,
        "person_id": str(person_id),
        "doctrine": {
            "hierarchy": ["privy_ledger", "portfolio_engine", "portfolio_breakdown_api", "ui"],
            "operational_source_of_truth": [
                "available",
                "in_vaults",
                "in_bundles",
                "locked_collateral",
                "debt",
                "pending_settlement",
            ],
            "total_holdings_formula": "available + in_vaults + locked_collateral",
            "total_holdings_note": "Recalculé depuis les scopes PE — pas un champ magique ledger.",
            "swappable_formula": "min(on_chain_balance_base, wallet_ledger_balance - locked_collateral)",
            "swap_max_field": "swappable_balance",
        },
        "warnings": [
            "Les champs breakdown ne sont pas forcément additifs.",
            "Certaines composantes représentent des sous-scopes économiques du wallet (bundle ⊂ wallet).",
            "Le breakdown est explicatif, pas comptable.",
        ],
        "non_additive_components": ["in_bundles", "debt", "pending_settlement"],
        "assets": assets,
        "swappable_by_asset": swappable_by_asset,
    }


def swappable_balance_map(db: Session, person_id: UUID) -> dict[str, str]:
    """Map asset → swappable_balance (pour enrichissement crypto-positions / swap MAX)."""
    breakdown = build_portfolio_breakdown(db, person_id)
    return dict(breakdown.get("swappable_by_asset") or {})
