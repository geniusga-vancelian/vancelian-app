"""Compare expected legacy-derived scopes vs current PE — dry-run gaps."""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from .bundle import compute_expected_bundle_scope_movements
from .enums import InternalScope
from .lombard import compute_expected_lombard_scope_movements
from .pe_reader import read_current_pe_scope_snapshot
from .types import CurrentPeScopeSnapshot, DoubleCountingRisk, ScopeGap, ScopeMovementSet
from .utils import (
    TOLERANCE,
    normalize_asset,
    user_vault_positions_table_exists,
)
from .vault import compute_expected_vault_scope_movements


def _scope_map(snap: CurrentPeScopeSnapshot, scope: str) -> dict[str, Decimal]:
    mapping = {
        InternalScope.TRADING_AVAILABLE.value: snap.trading_available,
        InternalScope.TRADING_LOCKED_COLLATERAL.value: snap.trading_locked_collateral,
        InternalScope.BUNDLE_CASH.value: snap.bundle_cash,
        InternalScope.BUNDLE_POSITION.value: snap.bundle_position,
        InternalScope.VAULT_POSITION.value: snap.vault_position,
        InternalScope.LIABILITY.value: snap.liability,
    }
    return mapping.get(scope, {})


def _net_expected_from_sets(*sets: ScopeMovementSet) -> dict[tuple[str, str], Decimal]:
    merged: dict[tuple[str, str], Decimal] = {}
    for s in sets:
        for key, qty in s.net_by_scope.items():
            merged[key] = merged.get(key, Decimal("0")) + qty
    return merged


def _read_legacy_vault_positions(db: Session, person_id: UUID) -> dict[str, Decimal]:
    if not user_vault_positions_table_exists(db):
        return {}
    rows = db.execute(
        sa.text(
            """
            SELECT asset_symbol, asset_decimals, principal_net_raw
            FROM user_vault_positions
            WHERE person_id = :person_id
            """
        ),
        {"person_id": str(person_id)},
    ).mappings().all()
    out: dict[str, Decimal] = {}
    for row in rows:
        asset = normalize_asset(row["asset_symbol"])
        raw = Decimal(str(row["principal_net_raw"] or "0"))
        dec = int(row["asset_decimals"] or 6)
        qty = raw / (Decimal(10) ** dec) if dec > 0 else raw
        if qty != 0:
            out[asset] = out.get(asset, Decimal("0")) + qty
    return out


def detect_double_counting_risks(
    db: Session,
    *,
    person_id: UUID,
    current: CurrentPeScopeSnapshot,
    expected_net: dict[tuple[str, str], Decimal],
    legacy_vault_uvp: dict[str, Decimal],
) -> list[DoubleCountingRisk]:
    risks: list[DoubleCountingRisk] = []

    for asset, uvp_qty in legacy_vault_uvp.items():
        if uvp_qty <= 0:
            continue
        pe_vault = current.vault_position.get(asset, Decimal("0"))
        pe_trading = current.trading_available.get(asset, Decimal("0"))
        exp_vault = expected_net.get((InternalScope.VAULT_POSITION.value, asset), Decimal("0"))

        if pe_vault <= TOLERANCE and exp_vault > TOLERANCE:
            risks.append(
                DoubleCountingRisk(
                    risk_type="vault_legacy_without_pe_scope",
                    asset=asset,
                    message=(
                        f"OVT/UVP indique {exp_vault} {asset} en vault mais aucun atom PE vault_position; "
                        f"trading_available PE ({pe_trading}) peut surévaluer la liquidité."
                    ),
                    metadata={
                        "legacy_user_vault_position": str(uvp_qty),
                        "expected_vault_scope": str(exp_vault),
                        "pe_vault_position": str(pe_vault),
                    },
                )
            )

        if uvp_qty > TOLERANCE and pe_vault > TOLERANCE and abs(uvp_qty - pe_vault) > TOLERANCE:
            risks.append(
                DoubleCountingRisk(
                    risk_type="vault_uvp_and_pe_vault_mismatch",
                    asset=asset,
                    message="user_vault_positions et PE vault_position divergent (futur risque double comptage).",
                    metadata={"uvp": str(uvp_qty), "pe_vault": str(pe_vault)},
                )
            )

    for (scope, asset), exp_qty in expected_net.items():
        if scope != InternalScope.TRADING_LOCKED_COLLATERAL.value or exp_qty <= TOLERANCE:
            continue
        pe_locked = current.trading_locked_collateral.get(asset, Decimal("0"))
        if pe_locked <= TOLERANCE:
            risks.append(
                DoubleCountingRisk(
                    risk_type="lombard_lock_legacy_without_pe_scope",
                    asset=asset,
                    message=(
                        f"Collateral Lombard attendu {exp_qty} {asset} locked mais PE trading_locked_collateral=0; "
                        "overlay UI seul — pas de scope PE."
                    ),
                    metadata={"expected_locked": str(exp_qty)},
                )
            )

    for asset, pe_trading in current.trading_available.items():
        bundle_cash = current.bundle_cash.get(asset, Decimal("0"))
        vault_pe = current.vault_position.get(asset, Decimal("0"))
        uvp = legacy_vault_uvp.get(asset, Decimal("0"))
        if bundle_cash > TOLERANCE and vault_pe <= TOLERANCE and uvp > TOLERANCE:
            risks.append(
                DoubleCountingRisk(
                    risk_type="usdc_bundle_cash_and_vault_uvp_coexist",
                    asset=asset,
                    message=(
                        "USDC en bundle_cash PE et encours vault UVP simultanés — "
                        "vérifier formule custody privy − bundle_cash − vault."
                    ),
                    severity="info",
                    metadata={
                        "bundle_cash": str(bundle_cash),
                        "uvp_vault": str(uvp),
                    },
                )
            )

    return risks


def compare_expected_scopes_vs_current_pe(
    db: Session,
    person_id: UUID,
) -> dict[str, Any]:
    vault_set = compute_expected_vault_scope_movements(db, person_id)
    lombard_set = compute_expected_lombard_scope_movements(db, person_id)
    bundle_set = compute_expected_bundle_scope_movements(db, person_id)
    current = read_current_pe_scope_snapshot(db, person_id)
    expected_net = _net_expected_from_sets(vault_set, lombard_set)

    gaps: list[ScopeGap] = []
    for (scope, asset), exp_qty in expected_net.items():
        if abs(exp_qty) <= TOLERANCE:
            continue
        current_map = _scope_map(current, scope)
        cur_qty = current_map.get(asset, Decimal("0"))
        if abs(cur_qty - exp_qty) > TOLERANCE:
            # Lombard lock : le débit trading_available legacy est un delta net,
            # pas un solde absolu PE (collateral pré-existant en trading_available).
            if (
                scope == InternalScope.TRADING_AVAILABLE.value
                and exp_qty < 0
            ):
                locked_exp = expected_net.get(
                    (InternalScope.TRADING_LOCKED_COLLATERAL.value, asset),
                    Decimal("0"),
                )
                locked_cur = current.trading_locked_collateral.get(asset, Decimal("0"))
                if locked_exp > TOLERANCE and abs(locked_cur - locked_exp) <= TOLERANCE:
                    continue
            gaps.append(
                ScopeGap(
                    gap_type="scope_pe_missing_or_divergent",
                    asset=asset,
                    expected_scope=scope,
                    expected_quantity=exp_qty,
                    current_quantity=cur_qty,
                    metadata={
                        "delta": str(exp_qty - cur_qty),
                        "source": "legacy_ovt_derived",
                    },
                )
            )

    for issue in lombard_set.collateral_parse_issues:
        gaps.append(
            ScopeGap(
                gap_type="missing_decimals_gap",
                asset=normalize_asset(str(issue.get("asset") or "UNKNOWN")),
                expected_scope=InternalScope.TRADING_LOCKED_COLLATERAL.value,
                expected_quantity=Decimal("0"),
                current_quantity=Decimal("0"),
                severity="warning",
                metadata=issue,
            )
        )

    legacy_vault = _read_legacy_vault_positions(db, person_id)
    for asset, uvp_qty in legacy_vault.items():
        pe_vault = current.vault_position.get(asset, Decimal("0"))
        exp_vault = expected_net.get((InternalScope.VAULT_POSITION.value, asset), Decimal("0"))
        ref = exp_vault if exp_vault > TOLERANCE else uvp_qty
        if ref > TOLERANCE and pe_vault <= TOLERANCE:
            gaps.append(
                ScopeGap(
                    gap_type="vault_position_not_in_pe",
                    asset=asset,
                    expected_scope=InternalScope.VAULT_POSITION.value,
                    expected_quantity=ref,
                    current_quantity=pe_vault,
                    metadata={"user_vault_positions": str(uvp_qty)},
                )
            )

    double_counting = detect_double_counting_risks(
        db,
        person_id=person_id,
        current=current,
        expected_net=expected_net,
        legacy_vault_uvp=legacy_vault,
    )

    expected_summary = {
        "vault_position": {},
        "trading_locked_collateral": {},
        "liability": {},
        "trading_available_net_from_legacy": {},
    }
    for (scope, asset), qty in expected_net.items():
        if scope == InternalScope.VAULT_POSITION.value:
            expected_summary["vault_position"][asset] = str(qty)
        elif scope == InternalScope.TRADING_LOCKED_COLLATERAL.value:
            expected_summary["trading_locked_collateral"][asset] = str(qty)
        elif scope == InternalScope.LIABILITY.value:
            expected_summary["liability"][asset] = str(qty)
        elif scope == InternalScope.TRADING_AVAILABLE.value:
            expected_summary["trading_available_net_from_legacy"][asset] = str(qty)

    return {
        "person_id": str(person_id),
        "dry_run": True,
        "current_pe": current.to_dict(),
        "expected_from_legacy": expected_summary,
        "legacy_user_vault_positions": {k: str(v) for k, v in legacy_vault.items()},
        "vault_movements": vault_set.to_dict(),
        "lombard_movements": lombard_set.to_dict(),
        "bundle_movements": bundle_set.to_dict(),
        "gaps": [g.to_dict() for g in gaps],
        "double_counting_risks": [r.to_dict() for r in double_counting],
        "summary": {
            "gap_count": len(gaps),
            "double_counting_risk_count": len(double_counting),
            "vault_movement_count": len(vault_set.movements),
            "lombard_movement_count": len(lombard_set.movements),
            "bundle_movement_count": len(bundle_set.movements),
        },
    }
