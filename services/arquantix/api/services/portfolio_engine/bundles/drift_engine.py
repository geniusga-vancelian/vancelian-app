"""Portfolio Drift Engine — lecture seule (Bundle V3 PR-1).

Le portefeuille (PE spot + cash leg + allocations cibles) est la seule vérité métier.
Drift et cibles calculés sur la NAV totale (``portfolio_value`` = spot + cash leg).
Aucun batch, swap ou leg historique n'entre dans le calcul.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any, Callable, Optional, Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.service import ExchangeService
from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundles.orchestrator import (
    POSITION_TYPE_CASH,
    POSITION_TYPE_SPOT,
    BundleOrchestrator,
)
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.positions.models import PositionAtom

BPS_SCALE = 10_000
PRICE_SOURCE_EXCHANGE_EUR = "exchange_service_eur_to_entry_asset"
WEIGHT_BASIS_PORTFOLIO_VALUE = "portfolio_value"
"""Poids et cibles sur la NAV totale (spot + cash leg). Le cash leg n'a pas de poids cible mais entre dans le dénominateur."""
WEIGHT_BASIS_INVESTED_ASSETS = "invested_assets"
"""Alias historique — préférer WEIGHT_BASIS_PORTFOLIO_VALUE."""


class PriceResolver(Protocol):
    def resolve_price_eur(self, asset: str) -> Decimal: ...


@dataclass(frozen=True)
class BundleDriftPriceSnapshot:
    """Prix utilisés pour le snapshot (audit / hash)."""

    entry_asset: str
    entry_asset_price_eur: str
    asset_prices_eur: dict[str, str]
    price_source: str = PRICE_SOURCE_EXCHANGE_EUR

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_asset": self.entry_asset,
            "entry_asset_price_eur": self.entry_asset_price_eur,
            "asset_prices_eur": dict(sorted(self.asset_prices_eur.items())),
            "price_source": self.price_source,
        }


@dataclass
class BundleDriftAsset:
    asset: str
    instrument_id: str
    target_weight_bps: int
    current_value_usdc: Decimal
    target_value_usdc: Decimal
    delta_value_usdc: Decimal
    current_weight_bps: int
    drift_bps: int
    current_quantity: str
    price_usdc: str
    action_hint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset,
            "instrument_id": self.instrument_id,
            "target_weight_bps": self.target_weight_bps,
            "current_value_usdc": _dec_str(self.current_value_usdc),
            "target_value_usdc": _dec_str(self.target_value_usdc),
            "delta_value_usdc": _dec_str(self.delta_value_usdc),
            "current_weight_bps": self.current_weight_bps,
            "drift_bps": self.drift_bps,
            "current_quantity": self.current_quantity,
            "price_usdc": self.price_usdc,
            "action_hint": self.action_hint,
        }


@dataclass
class BundleDriftNonTargetAsset:
    asset: str
    instrument_id: str
    current_value_usdc: Decimal
    current_quantity: str
    price_usdc: str
    current_weight_bps: int
    action_hint: str = "sell_candidate"

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset,
            "instrument_id": self.instrument_id,
            "current_value_usdc": _dec_str(self.current_value_usdc),
            "current_quantity": self.current_quantity,
            "price_usdc": self.price_usdc,
            "current_weight_bps": self.current_weight_bps,
            "action_hint": self.action_hint,
        }


@dataclass
class BundleDriftSnapshot:
    portfolio_id: str
    client_id: str
    portfolio_value_usdc: Decimal
    invested_value_usdc: Decimal
    cash_value_usdc: Decimal
    entry_asset: str
    weight_basis: str = WEIGHT_BASIS_PORTFOLIO_VALUE
    target_assets: list[BundleDriftAsset] = field(default_factory=list)
    non_target_assets: list[BundleDriftNonTargetAsset] = field(default_factory=list)
    cash_asset: dict[str, str] = field(default_factory=dict)
    computed_at: str = ""
    price_source: str = PRICE_SOURCE_EXCHANGE_EUR
    snapshot_hash: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "client_id": self.client_id,
            "weight_basis": self.weight_basis,
            "invested_value_usdc": _dec_str(self.invested_value_usdc),
            "portfolio_value_usdc": _dec_str(self.portfolio_value_usdc),
            "cash_value_usdc": _dec_str(self.cash_value_usdc),
            "entry_asset": self.entry_asset,
            "target_assets": [a.to_dict() for a in self.target_assets],
            "non_target_assets": [a.to_dict() for a in self.non_target_assets],
            "cash_asset": dict(self.cash_asset),
            "computed_at": self.computed_at,
            "price_source": self.price_source,
            "snapshot_hash": self.snapshot_hash,
            "warnings": list(self.warnings),
        }


# Alias PRD — plan read-only = snapshot sérialisé
BundleDriftPlan = BundleDriftSnapshot


def _dec_str(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.000001"), rounding=ROUND_DOWN), "f")


def _weight_to_bps(weight: Decimal) -> int:
    return int((weight * BPS_SCALE).to_integral_value(rounding=ROUND_DOWN))


def _value_bps(part: Decimal, whole: Decimal) -> int:
    if whole <= 0:
        return 0
    return int((part * BPS_SCALE / whole).to_integral_value(rounding=ROUND_DOWN))


def _action_hint(
    delta: Decimal,
    *,
    portfolio_value_usdc: Decimal,
    target_weight_bps: int,
) -> str:
    if portfolio_value_usdc <= 0 and target_weight_bps > 0:
        return "buy"
    if delta > 0:
        return "buy"
    if delta < 0:
        return "sell"
    return "hold"


def _eur_to_entry_asset(value_eur: Decimal, entry_price_eur: Decimal) -> Decimal:
    if value_eur <= 0:
        return Decimal("0")
    if entry_price_eur <= 0:
        return Decimal("0")
    return (value_eur / entry_price_eur).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)


def _canonical_hash_payload(
    *,
    portfolio_id: str,
    client_id: str,
    entry_asset: str,
    weight_basis: str,
    invested_value_usdc: str,
    cash_value_usdc: str,
    target_assets: list[dict[str, Any]],
    non_target_assets: list[dict[str, Any]],
    price_snapshot: dict[str, Any],
) -> str:
    body = {
        "portfolio_id": portfolio_id,
        "client_id": client_id,
        "entry_asset": entry_asset,
        "weight_basis": weight_basis,
        "invested_value_usdc": invested_value_usdc,
        "cash_value_usdc": cash_value_usdc,
        "target_assets": target_assets,
        "non_target_assets": non_target_assets,
        "price_snapshot": price_snapshot,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


class _ExchangePriceResolver:
    def __init__(self, db: Session, exchange: ExchangeService):
        self._db = db
        self._exchange = exchange

    def resolve_price_eur(self, asset: str) -> Decimal:
        return self._exchange._resolve_price(self._db, asset, override_price=None, side="sell")


def compute_bundle_drift_snapshot(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    exchange_service: Optional[ExchangeService] = None,
    price_resolver: Optional[PriceResolver] = None,
    computed_at: Optional[datetime] = None,
) -> dict[str, Any]:
    """Calcule un snapshot drift read-only — aucune écriture DB."""
    portfolio = BundleOrchestrator._load_and_validate_portfolio(db, portfolio_id, client_id)
    product = BundleOrchestrator._load_product(db, portfolio)
    entry_config = BundleOrchestrator._resolve_entry_config(product)
    entry_asset = str(entry_config["entry_asset_default"]).upper()

    resolver: PriceResolver
    if price_resolver is not None:
        resolver = price_resolver
    else:
        resolver = _ExchangePriceResolver(db, exchange_service or ExchangeService())

    allocations = BundleOrchestrator._load_target_allocations(db, portfolio_id)
    warnings: list[str] = []
    if not allocations:
        warnings.append("no_target_allocations_found")

    atoms = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.status == "open",
        )
        .all()
    )

    instrument_cache: dict[UUID, tuple[Instrument, Asset]] = {}
    target_instrument_ids: set[UUID] = {a.instrument_id for a in allocations}

    for atom in atoms:
        if atom.instrument_id not in instrument_cache:
            instr = db.query(Instrument).filter(Instrument.id == atom.instrument_id).first()
            asset_obj = (
                db.query(Asset).filter(Asset.id == instr.asset_id).first() if instr else None
            )
            if instr and asset_obj:
                instrument_cache[atom.instrument_id] = (instr, asset_obj)

    cash_leg_qty = Decimal("0")
    spot_by_instrument: dict[UUID, Decimal] = {}

    for atom in atoms:
        if atom.instrument_id not in instrument_cache:
            continue
        qty = Decimal(str(atom.quantity))
        if atom.position_type == POSITION_TYPE_CASH:
            cash_leg_qty += qty
        elif atom.position_type == POSITION_TYPE_SPOT:
            spot_by_instrument[atom.instrument_id] = (
                spot_by_instrument.get(atom.instrument_id, Decimal("0")) + qty
            )

    try:
        entry_price_eur = resolver.resolve_price_eur(entry_asset)
    except Exception as exc:
        warnings.append(f"entry_price_unavailable:{entry_asset}:{exc}")
        entry_price_eur = Decimal("0")

    cash_value_usdc = _eur_to_entry_asset(cash_leg_qty * entry_price_eur, entry_price_eur)
    if entry_asset == "USDC" and entry_price_eur > 0:
        cash_value_usdc = cash_leg_qty.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)

    price_eur_cache: dict[str, Decimal] = {entry_asset: entry_price_eur}
    target_rows: list[BundleDriftAsset] = []
    total_spot_usdc = Decimal("0")

    for alloc in allocations:
        instr, asset_obj = instrument_cache.get(alloc.instrument_id, (None, None))
        if instr is None or asset_obj is None:
            instr = db.query(Instrument).filter(Instrument.id == alloc.instrument_id).first()
            asset_obj = (
                db.query(Asset).filter(Asset.id == instr.asset_id).first() if instr else None
            )
        if instr is None or asset_obj is None:
            warnings.append(f"instrument_not_found:{alloc.instrument_id}")
            continue

        symbol = BundleOrchestrator._normalize_asset_symbol(asset_obj.symbol.upper())
        qty = spot_by_instrument.get(alloc.instrument_id, Decimal("0"))

        if symbol not in price_eur_cache:
            try:
                price_eur_cache[symbol] = resolver.resolve_price_eur(symbol)
            except Exception as exc:
                warnings.append(f"price_unavailable:{symbol}:{exc}")
                price_eur_cache[symbol] = Decimal("0")

        price_eur = price_eur_cache[symbol]
        value_eur = qty * price_eur
        price_usdc = _eur_to_entry_asset(Decimal("1") * price_eur, entry_price_eur) if price_eur > 0 else Decimal("0")
        if entry_asset == symbol and entry_price_eur > 0:
            price_usdc = Decimal("1")
        current_value_usdc = _eur_to_entry_asset(value_eur, entry_price_eur)
        total_spot_usdc += current_value_usdc

        target_weight_bps = _weight_to_bps(Decimal(str(alloc.target_weight)))
        target_rows.append(
            BundleDriftAsset(
                asset=symbol,
                instrument_id=str(alloc.instrument_id),
                target_weight_bps=target_weight_bps,
                current_value_usdc=current_value_usdc,
                target_value_usdc=Decimal("0"),
                delta_value_usdc=Decimal("0"),
                current_weight_bps=0,
                drift_bps=0,
                current_quantity=_dec_str(qty),
                price_usdc=_dec_str(price_usdc),
                action_hint="hold",
            )
        )

    invested_value_usdc = total_spot_usdc
    portfolio_value_usdc = invested_value_usdc + cash_value_usdc
    weight_denominator = portfolio_value_usdc

    for row in target_rows:
        if weight_denominator > 0:
            target_value = (
                weight_denominator * Decimal(row.target_weight_bps) / BPS_SCALE
            ).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
            row.current_weight_bps = _value_bps(row.current_value_usdc, weight_denominator)
        else:
            target_value = Decimal("0")
            row.current_weight_bps = 0
        delta = (target_value - row.current_value_usdc).quantize(
            Decimal("0.000001"), rounding=ROUND_DOWN,
        )
        row.target_value_usdc = target_value
        row.delta_value_usdc = delta
        row.drift_bps = row.current_weight_bps - row.target_weight_bps
        row.action_hint = _action_hint(
            delta,
            portfolio_value_usdc=portfolio_value_usdc,
            target_weight_bps=row.target_weight_bps,
        )

    non_target: list[BundleDriftNonTargetAsset] = []
    for instrument_id, qty in spot_by_instrument.items():
        if instrument_id in target_instrument_ids:
            continue
        instr, asset_obj = instrument_cache.get(instrument_id, (None, None))
        if asset_obj is None:
            continue
        symbol = BundleOrchestrator._normalize_asset_symbol(asset_obj.symbol.upper())
        if symbol not in price_eur_cache:
            try:
                price_eur_cache[symbol] = resolver.resolve_price_eur(symbol)
            except Exception as exc:
                warnings.append(f"price_unavailable:{symbol}:{exc}")
                price_eur_cache[symbol] = Decimal("0")
        price_eur = price_eur_cache[symbol]
        value_usdc = _eur_to_entry_asset(qty * price_eur, entry_price_eur)
        non_target.append(
            BundleDriftNonTargetAsset(
                asset=symbol,
                instrument_id=str(instrument_id),
                current_value_usdc=value_usdc,
                current_quantity=_dec_str(qty),
                price_usdc=_dec_str(
                    _eur_to_entry_asset(price_eur, entry_price_eur) if price_eur > 0 else Decimal("0")
                ),
                current_weight_bps=_value_bps(value_usdc, weight_denominator),
            )
        )

    non_target.sort(key=lambda r: r.asset)
    target_rows.sort(key=lambda r: r.asset)

    price_snapshot = BundleDriftPriceSnapshot(
        entry_asset=entry_asset,
        entry_asset_price_eur=_dec_str(entry_price_eur),
        asset_prices_eur={k: _dec_str(v) for k, v in sorted(price_eur_cache.items())},
    )

    computed_iso = (computed_at or datetime.now(timezone.utc)).isoformat()
    snapshot = BundleDriftSnapshot(
        portfolio_id=str(portfolio_id),
        client_id=str(client_id),
        portfolio_value_usdc=portfolio_value_usdc,
        invested_value_usdc=invested_value_usdc,
        cash_value_usdc=cash_value_usdc,
        entry_asset=entry_asset,
        weight_basis=WEIGHT_BASIS_PORTFOLIO_VALUE,
        target_assets=target_rows,
        non_target_assets=non_target,
        cash_asset={
            "asset": entry_asset,
            "current_value_usdc": _dec_str(cash_value_usdc),
        },
        computed_at=computed_iso,
        warnings=warnings,
    )

    hash_payload_targets = [
        {
            "asset": r.asset,
            "instrument_id": r.instrument_id,
            "target_weight_bps": r.target_weight_bps,
            "current_quantity": r.current_quantity,
            "current_value_usdc": _dec_str(r.current_value_usdc),
        }
        for r in target_rows
    ]
    hash_payload_non_target = [
        {
            "asset": r.asset,
            "instrument_id": r.instrument_id,
            "current_quantity": r.current_quantity,
            "current_value_usdc": _dec_str(r.current_value_usdc),
        }
        for r in non_target
    ]
    snapshot.snapshot_hash = _canonical_hash_payload(
        portfolio_id=str(portfolio_id),
        client_id=str(client_id),
        entry_asset=entry_asset,
        weight_basis=WEIGHT_BASIS_PORTFOLIO_VALUE,
        invested_value_usdc=_dec_str(invested_value_usdc),
        cash_value_usdc=_dec_str(cash_value_usdc),
        target_assets=hash_payload_targets,
        non_target_assets=hash_payload_non_target,
        price_snapshot=price_snapshot.to_dict(),
    )

    return snapshot.to_dict()
