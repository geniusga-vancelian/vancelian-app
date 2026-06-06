"""Audit lecture seule — réconciliation compte crypto (doctrine custody v2)."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from config.base_allowed_assets import BASE_ALLOWED_SYMBOLS, BASE_LIFI_CHAIN_ID
from database import Person, PersonExternalIdentity
from services.audit.legacy_frozen import assets_in_frozen_scope, load_frozen_scope, map_scope_gap_to_frozen_id
from services.cost_basis.models import CostBasisExecution
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_reconciliation import (
    build_reconciliation_dry_run_summary,
    detect_swap_ledger_legs,
    is_tx_confirmed_on_chain,
    swap_ledger_legs_complete,
)
from services.lifi.lifi_swap_settlement import swap_debit_idempotency_key
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.internal_scope_movements.compare import compare_expected_scopes_vs_current_pe
from services.portfolio_engine.internal_scope_movements.pe_reader import read_current_pe_scope_snapshot
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.privy_wallet.deposit_backfill import fetch_aggregated_on_chain_balances
from services.privy_wallet.evm_chain_config import CHAIN_LABELS, supported_pilot_chain_ids
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import PersonCryptoWalletRepository, PersonWalletBalanceRepository

logger = logging.getLogger(__name__)

AUDIT_VERSION = "custody_doctrine_v2"
DUST = Decimal("0.000001")
FOCUS_SWAP_ID = "76830776-039d-48a3-9e58-df48b0b10f7e"
STABLECOIN_PILOT_ASSETS = frozenset({"EURC", "USDC", "USDT"})
MULTI_CHAIN_LEDGER_ASSETS = frozenset({"USDT"})

INFORMATIONAL_TAGS = frozenset(
    {
        "bundle_overlap_expected",
        "vault_explains_delta",
        "active_debt",
        "collateral_locked_matches_wallet",
    }
)


def _fmt(value: Decimal | None) -> str:
    if value is None:
        return "0"
    text = format(Decimal(str(value)).normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _asset_tolerance(asset: str) -> Decimal:
    a = (asset or "").upper()
    if a in ("USDC", "USDT", "EURC", "DAI", "USDE"):
        return Decimal("0.01")
    if a in ("ETH", "CBETH", "CBBTC", "BTC", "WBTC"):
        return Decimal("0.00000001")
    return Decimal("0.000001")


def _effective_tolerance(asset: str, balance: Decimal) -> Decimal:
    pct = abs(balance) * Decimal("0.000001") if balance else Decimal("0")
    return max(_asset_tolerance(asset), pct)


def _price_usd(db: Session, asset: str) -> Decimal | None:
    try:
        from services.lending.product_surface import _get_price_eur
        from services.market_data.fx import get_eurusdt_rate

        eurusdt = get_eurusdt_rate(db, strict=False)
        price_usdt, _ = _get_price_eur(db, asset, eurusdt)
        return Decimal(str(price_usdt)) if price_usdt is not None else None
    except Exception:
        return None


def resolve_person_ids_by_email(db: Session, email: str) -> list[UUID]:
    needle = email.strip().lower()
    out: set[UUID] = set()
    for row in db.query(PersonExternalIdentity).filter(PersonExternalIdentity.external_email.ilike(needle)).all():
        out.add(row.person_id)
    for row in db.query(Client).filter(Client.email.ilike(needle)).all():
        if row.person_id:
            out.add(row.person_id)
    return sorted(out, key=str)


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
        return embedded[0], wallets
    privy = [w for w in wallets if (w.provider or "").lower() == "privy"]
    if privy:
        return privy[0], wallets
    return (wallets[0], wallets) if wallets else (None, wallets)


def _assets_for_onchain_scan(ledger: dict[str, Decimal]) -> list[str]:
    assets = set(BASE_ALLOWED_SYMBOLS) | set(ledger.keys())
    for asset, bal in ledger.items():
        if asset in MULTI_CHAIN_LEDGER_ASSETS and bal > DUST:
            assets.add(asset)
    return sorted(assets)


def _bundle_positions(db: Session, person_id: UUID) -> dict[str, Any]:
    client = db.query(Client).filter(Client.person_id == person_id).first()
    if client is None:
        return {"positions": [], "mismatches": []}
    bundles = (
        db.query(Portfolio)
        .filter(
            Portfolio.client_id == client.id,
            Portfolio.portfolio_type == "bundle_portfolio",
            Portfolio.status == "active",
        )
        .all()
    )
    positions = []
    for pf in bundles:
        atoms = (
            db.query(PositionAtom)
            .filter(PositionAtom.portfolio_id == pf.id, PositionAtom.status == "open")
            .all()
        )
        for atom in atoms:
            meta = atom.metadata_ if isinstance(atom.metadata_, dict) else {}
            positions.append(
                {
                    "portfolio_id": str(pf.id),
                    "portfolio_code": getattr(pf, "code", None) or getattr(pf, "name", None),
                    "atom_id": str(atom.id),
                    "position_type": atom.position_type,
                    "quantity": _fmt(Decimal(str(atom.quantity or 0))),
                    "available": _fmt(Decimal(str(atom.available_quantity or atom.quantity or 0))),
                    "locked": _fmt(Decimal(str(atom.locked_quantity or 0))),
                    "metadata_role": meta.get("role"),
                }
            )
    return {"positions": positions, "mismatches": []}


def _swap_issues(db: Session, person_id: UUID) -> dict[str, Any]:
    submitted_confirmed: list[dict[str, Any]] = []
    confirmed_incomplete: list[dict[str, Any]] = []
    failed_insufficient: list[dict[str, Any]] = []

    swaps = (
        db.query(PersonWalletSwap)
        .filter(PersonWalletSwap.person_id == person_id)
        .order_by(PersonWalletSwap.updated_at.desc())
        .limit(200)
        .all()
    )
    for swap in swaps:
        legs = detect_swap_ledger_legs(db, swap)
        entry = {
            "swap_id": str(swap.id),
            "status": swap.status,
            "from_asset": swap.from_asset,
            "to_asset": swap.to_asset,
            "amount_in": _fmt(Decimal(str(swap.amount_in or 0))),
            "tx_hash": swap.tx_hash,
            "debit_exists": legs.debit_exists,
            "credit_exists": legs.credit_exists,
        }
        if swap.status == SwapSessionStatus.SUBMITTED.value and swap.tx_hash and is_tx_confirmed_on_chain(swap):
            if not (legs.debit_exists and legs.credit_exists):
                submitted_confirmed.append(entry)
        if swap.status == SwapSessionStatus.CONFIRMED.value and not (legs.debit_exists and legs.credit_exists):
            confirmed_incomplete.append(entry)
        err = str(swap.error_message or "").lower()
        if swap.status == SwapSessionStatus.FAILED.value and "insufficient" in err:
            failed_insufficient.append(entry)
    return {
        "submitted_confirmed_onchain": submitted_confirmed,
        "confirmed_incomplete_settlement": confirmed_incomplete,
        "failed_after_insufficient_funds": failed_insufficient,
    }


def _cost_basis_audit(db: Session, person_id: UUID) -> dict[str, Any]:
    swaps = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == person_id,
            PersonWalletSwap.status == SwapSessionStatus.CONFIRMED.value,
        )
        .all()
    )
    missing = []
    for swap in swaps:
        prefix = f"lifi:{swap.id}:"
        count = (
            db.query(CostBasisExecution)
            .filter(CostBasisExecution.provider_execution_id.like(f"{prefix}%"))
            .count()
        )
        if count == 0:
            missing.append({"swap_id": str(swap.id), "pair": f"{swap.from_asset}->{swap.to_asset}"})
    rows = (
        db.query(CostBasisExecution.provider_execution_id, CostBasisExecution.id)
        .filter(CostBasisExecution.person_id == person_id)
        .all()
    )
    seen: dict[str, list[str]] = {}
    for peid, cid in rows:
        seen.setdefault(peid, []).append(str(cid))
    duplicates = [{"provider_execution_id": k, "ids": v} for k, v in seen.items() if len(v) > 1]
    return {"missing": missing, "duplicates": duplicates}


def _focus_swap(db: Session, swap_id: str) -> dict[str, Any] | None:
    swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == UUID(swap_id)).first()
    if swap is None:
        return None
    legs = detect_swap_ledger_legs(db, swap)
    debit_key = swap_debit_idempotency_key(swap_id)
    debit = (
        db.query(PersonWalletDeposit)
        .filter(PersonWalletDeposit.idempotency_key == debit_key)
        .first()
    )
    return {
        "swap_id": swap_id,
        "status": swap.status,
        "tx_hash": swap.tx_hash,
        "legs": {
            "debit_exists": legs.debit_exists,
            "credit_exists": legs.credit_exists,
            "debit_deposit_id": str(legs.debit_deposit_id) if legs.debit_deposit_id else None,
            "credit_deposit_id": str(legs.credit_deposit_id) if legs.credit_deposit_id else None,
        },
        "debit_by_idempotency_key": {
            "exists": debit is not None,
            "log_index": debit.log_index if debit else None,
            "amount": _fmt(Decimal(str(debit.amount))) if debit else None,
        },
        "ledger_complete": swap_ledger_legs_complete(db, swap),
        "dry_run_preview": build_reconciliation_dry_run_summary(db, swap),
    }


def _classify_raw_asset_signals(
    *,
    asset: str,
    ledger_bal: Decimal,
    chain_bal: Decimal,
    ledger_liquid: Decimal,
    vault_alloc: Decimal,
    bundle_alloc: Decimal,
    collateral: Decimal,
    debt: Decimal,
    direct_avail: Decimal,
    delta_liquid: Decimal,
    tol: Decimal,
    chain_ids_scanned: list[int],
) -> tuple[list[str], list[str], list[str]]:
    """Retourne (custody_issues, informational, legacy_candidates)."""
    custody: list[str] = []
    informational: list[str] = []
    legacy_candidates: list[str] = []

    if abs(delta_liquid) > tol and (chain_bal > DUST or ledger_liquid > DUST):
        if assets_in_frozen_scope(asset) and collateral > DUST:
            legacy_candidates.append("ledger_liquid_vs_onchain_collateral_legacy")
        else:
            custody.append("ledger_liquid_vs_onchain")

    if chain_bal > DUST and ledger_bal <= DUST:
        custody.append("onchain_without_ledger")

    if ledger_bal > DUST and chain_bal <= DUST and vault_alloc <= DUST:
        if collateral <= DUST and bundle_alloc <= DUST:
            if asset in MULTI_CHAIN_LEDGER_ASSETS and 1 not in chain_ids_scanned:
                informational.append("missing_chain_scope")
            else:
                custody.append("ledger_without_onchain")

    if vault_alloc > DUST and abs(ledger_bal - chain_bal) > tol and abs(delta_liquid) <= tol:
        informational.append("vault_explains_delta")

    if bundle_alloc > DUST and ledger_bal > DUST:
        informational.append("bundle_overlap_expected")

    if debt > DUST:
        informational.append("active_debt")

    if collateral > DUST and abs(chain_bal - collateral) <= tol and direct_avail <= DUST:
        informational.append("collateral_locked_matches_wallet")

    if collateral > DUST and direct_avail > DUST:
        custody.append("collateral_and_direct_available_overlap")

    return custody, informational, legacy_candidates


def _collect_legacy_frozen(scope_compare: dict[str, Any]) -> list[dict[str, Any]]:
    frozen: list[dict[str, Any]] = []
    for gap in scope_compare.get("gaps", []):
        asset = str(gap.get("asset") or "")
        frozen.append(
            {
                "type": "legacy_frozen",
                "frozen_scope_id": map_scope_gap_to_frozen_id(
                    str(gap.get("gap_type") or ""),
                    str(gap.get("expected_scope") or "") or None,
                ),
                "asset": asset,
                "gap_type": gap.get("gap_type"),
                "expected_scope": gap.get("expected_scope"),
                "expected_quantity": gap.get("expected_quantity"),
                "current_quantity": gap.get("current_quantity"),
                "do_not_auto_fix": True,
            }
        )
    for risk in scope_compare.get("double_counting_risks", []):
        frozen.append(
            {
                "type": "legacy_frozen",
                "frozen_scope_id": str(risk.get("risk_type") or "double_counting"),
                "asset": risk.get("asset"),
                "message": risk.get("message"),
                "severity": risk.get("severity"),
                "metadata": risk.get("metadata"),
                "do_not_auto_fix": True,
            }
        )
    return frozen


def _build_success_criteria(
    db: Session,
    *,
    asset_rows: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    informational: list[dict[str, Any]],
    reporting_gaps: list[dict[str, Any]],
    legacy_frozen: list[dict[str, Any]],
    swaps: dict[str, Any],
) -> dict[str, Any]:
    liquid_delta_usd = Decimal("0")
    stablecoin_ok = True

    for row in asset_rows:
        asset = row["asset"]
        delta_liquid = Decimal(str(row.get("delta_ledger_liquid_vs_onchain") or "0"))
        tol = Decimal(str(row.get("custody_tolerance") or "0"))
        ledger_liquid = Decimal(str(row.get("ledger_liquid") or "0"))
        chain_bal = Decimal(str(row.get("on_chain_balance") or "0"))

        if abs(delta_liquid) > tol and (ledger_liquid > DUST or chain_bal > DUST):
            px = _price_usd(db, asset)
            if px is not None:
                liquid_delta_usd += abs(delta_liquid) * px

        if asset in STABLECOIN_PILOT_ASSETS and (ledger_liquid > DUST or chain_bal > DUST):
            missing_chain = "missing_chain_scope" in (row.get("informational") or [])
            if abs(delta_liquid) > tol and not missing_chain:
                stablecoin_ok = False

    swap_blockers = bool(swaps.get("confirmed_incomplete_settlement") or swaps.get("submitted_confirmed_onchain"))
    custody_reconciled = stablecoin_ok and not issues and not swap_blockers

    return {
        "custody_reconciled": custody_reconciled,
        "stablecoin_custody_ok": stablecoin_ok,
        "liquid_wallet_delta_usd": _fmt(liquid_delta_usd.quantize(Decimal("0.01"))),
        "reporting_gaps_count": len(reporting_gaps),
        "legacy_frozen_count": len(legacy_frozen),
        "informational_count": len(informational),
        "custody_issue_count": len(issues),
        "fully_reconciled": custody_reconciled,
        "global_delta_usd": None,
        "global_delta_usd_deprecated": "use liquid_wallet_delta_usd (custody-only)",
    }


def _classify_recommendations(
    report: dict[str, Any],
    *,
    frozen_scope: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    safe: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    forbidden: list[dict[str, Any]] = []

    for swap in report.get("swaps", {}).get("confirmed_incomplete_settlement", []):
        safe.append(
            {
                "type": "swap_settlement_repair",
                "swap_id": swap["swap_id"],
                "reason": "CONFIRMED avec jambes ledger incomplètes — candidat settle_lifi_swap_idempotently",
            }
        )
    for swap in report.get("swaps", {}).get("submitted_confirmed_onchain", []):
        safe.append(
            {
                "type": "swap_submitted_reconcile",
                "swap_id": swap["swap_id"],
                "reason": "SUBMITTED + tx confirmée on-chain — candidat réconciliation idempotente",
            }
        )

    for gap in report.get("reporting_gaps", []):
        review.append({**gap, "category": "reporting_gap"})

    for issue in report.get("issues", []):
        review.append({"type": "custody_issue", **issue})

    for entry in report.get("legacy_frozen", []):
        forbidden.append(
            {
                "type": "legacy_frozen",
                "frozen_scope_id": entry.get("frozen_scope_id"),
                "asset": entry.get("asset"),
                "do_not_auto_fix": True,
                "reason": frozen_scope.get("requires_protocol_proof") and "requires_protocol_proof" or "legacy_frozen",
            }
        )

    return {"safe_auto": safe, "requires_review": review, "do_not_auto_fix": forbidden}


def build_person_crypto_audit(
    db: Session,
    *,
    email: str,
    prepare_fixes: bool = False,
) -> dict[str, Any]:
    """Audit lecture seule — doctrine custody v2."""
    frozen_scope = load_frozen_scope()
    person_ids = resolve_person_ids_by_email(db, email)
    if not person_ids:
        return {"error": f"Aucune personne pour email={email}"}
    if len(person_ids) > 1:
        return {"error": f"Plusieurs person_id pour {email}", "person_ids": [str(p) for p in person_ids]}

    person_id = person_ids[0]
    person = db.query(Person).filter(Person.id == person_id).first()
    client = db.query(Client).filter(Client.person_id == person_id).first()
    primary_wallet, all_wallets = _pick_privy_embedded_wallet(db, person_id)
    pe = read_current_pe_scope_snapshot(db, person_id)
    ledger = _ledger_balances(db, person_id)
    scope_compare = compare_expected_scopes_vs_current_pe(db, person_id)

    on_chain: dict[str, Decimal] = {}
    on_chain_by_chain: dict[str, dict[str, str]] = {}
    chain_ids_scanned: list[int] = []
    if primary_wallet and primary_wallet.address:
        scan_assets = _assets_for_onchain_scan(ledger)
        chain_ids = supported_pilot_chain_ids() or [BASE_LIFI_CHAIN_ID]
        chain_ids_scanned = list(chain_ids)
        raw = fetch_aggregated_on_chain_balances(
            wallet_address=primary_wallet.address,
            chain_ids=chain_ids,
            assets=scan_assets,
        )
        for (cid, asset), bal in raw.items():
            on_chain[asset] = on_chain.get(asset, Decimal("0")) + bal
            label = CHAIN_LABELS.get(cid, str(cid))
            on_chain_by_chain.setdefault(asset, {})[label] = _fmt(bal)

    asset_rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    informational: list[dict[str, Any]] = []

    all_assets = sorted(
        set(ledger.keys())
        | set(on_chain.keys())
        | set(pe.trading_available.keys())
        | set(pe.vault_position.keys())
    )

    for asset in all_assets:
        ledger_bal = ledger.get(asset, Decimal("0"))
        chain_bal = on_chain.get(asset, Decimal("0"))
        direct_avail = pe.trading_available.get(asset, Decimal("0"))
        vault_alloc = pe.vault_position.get(asset, Decimal("0"))
        bundle_alloc = pe.bundle_cash.get(asset, Decimal("0")) + pe.bundle_position.get(asset, Decimal("0"))
        collateral = pe.trading_locked_collateral.get(asset, Decimal("0"))
        debt = pe.liability.get(asset, Decimal("0"))
        ledger_liquid = ledger_bal - vault_alloc
        ledger_spendable = max(ledger_bal - collateral, Decimal("0"))
        swappable = min(chain_bal, ledger_spendable) if chain_bal > 0 else ledger_spendable
        delta_liquid = ledger_liquid - chain_bal
        tol = _effective_tolerance(asset, max(chain_bal, ledger_liquid, ledger_bal))
        custody_ok = abs(delta_liquid) <= tol or (chain_bal <= DUST and ledger_liquid <= DUST)

        custody_tags, info_tags, legacy_tags = _classify_raw_asset_signals(
            asset=asset,
            ledger_bal=ledger_bal,
            chain_bal=chain_bal,
            ledger_liquid=ledger_liquid,
            vault_alloc=vault_alloc,
            bundle_alloc=bundle_alloc,
            collateral=collateral,
            debt=debt,
            direct_avail=direct_avail,
            delta_liquid=delta_liquid,
            tol=tol,
            chain_ids_scanned=chain_ids_scanned,
        )

        for tag in custody_tags:
            issues.append(
                {
                    "type": "custody_issue",
                    "asset": asset,
                    "issue": tag,
                    "delta_ledger_liquid_vs_onchain": _fmt(delta_liquid),
                    "tolerance": _fmt(tol),
                }
            )
        for tag in info_tags:
            informational.append({"type": "informational", "asset": asset, "issue": tag})
        for tag in legacy_tags:
            informational.append({"type": "legacy_candidate", "asset": asset, "issue": tag})

        asset_rows.append(
            {
                "asset": asset,
                "on_chain_balance": _fmt(chain_bal),
                "ledger_balance": _fmt(ledger_bal),
                "ledger_liquid": _fmt(ledger_liquid),
                "vault_allocated": _fmt(vault_alloc),
                "direct_available": _fmt(direct_avail),
                "bundle_allocated": _fmt(bundle_alloc),
                "collateral_locked": _fmt(collateral),
                "debt": _fmt(debt),
                "swappable_balance": _fmt(swappable),
                "delta_ledger_liquid_vs_onchain": _fmt(delta_liquid),
                "custody_tolerance": _fmt(tol),
                "custody_reconciled": custody_ok and not custody_tags,
                "on_chain_by_chain": on_chain_by_chain.get(asset, {}),
                "custody_issues": custody_tags,
                "informational": info_tags,
            }
        )

    swaps = _swap_issues(db, person_id)
    bundles = _bundle_positions(db, person_id)
    cost_basis = _cost_basis_audit(db, person_id)
    focus = _focus_swap(db, FOCUS_SWAP_ID)
    legacy_frozen = _collect_legacy_frozen(scope_compare)

    reporting_gaps = [
        {"type": "cost_basis_missing", **row}
        for row in cost_basis.get("missing", [])
    ]

    loans = {
        "positions": [
            {"asset": k, "locked_collateral": _fmt(v)}
            for k, v in sorted(pe.trading_locked_collateral.items())
        ],
        "liabilities": [{"asset": k, "amount": _fmt(v)} for k, v in sorted(pe.liability.items())],
        "mismatches": [],
    }

    success_criteria = _build_success_criteria(
        db,
        asset_rows=asset_rows,
        issues=issues,
        informational=informational,
        reporting_gaps=reporting_gaps,
        legacy_frozen=legacy_frozen,
        swaps=swaps,
    )

    report: dict[str, Any] = {
        "audit_version": AUDIT_VERSION,
        "read_only": True,
        "person": {
            "email": email,
            "person_id": str(person_id),
            "account_state": getattr(person, "account_state", None),
            "client_id": str(client.id) if client else None,
        },
        "wallets": [
            {
                "id": str(w.id),
                "address": w.address,
                "provider": w.provider,
                "wallet_type": w.wallet_type,
                "chain_type": w.chain_type,
                "is_primary_for_audit": primary_wallet is not None and w.id == primary_wallet.id,
            }
            for w in all_wallets
        ],
        "accounting_doctrine": {
            "version": AUDIT_VERSION,
            "physical_truth": "wallet_privy_on_chain_multi_chain",
            "liquid_wallet_check": "ledger_liquid = ledger_privy - vault_position_PE == sum(on_chain_by_chain)",
            "bundle_scope": "economic_sub_ledger_subset_of_wallet",
            "vault_scope": "hors_wallet_erc20",
            "collateral_scope": "locked_non_spendable",
            "swappable_formula": "min(on_chain_wallet_balance, ledger_balance - collateral_locked)",
            "deprecated_formula": "direct+bundle+vault+collateral+pending=on_chain (invalid)",
            "chains_scanned": [CHAIN_LABELS.get(c, str(c)) for c in chain_ids_scanned],
        },
        "legacy_frozen_policy": {
            "legacy_frozen": frozen_scope.get("legacy_frozen"),
            "requires_protocol_proof": frozen_scope.get("requires_protocol_proof"),
            "do_not_auto_fix": frozen_scope.get("do_not_auto_fix"),
            "source": "docs/accounting/legacy/FROZEN_SCOPE.json",
        },
        "assets": asset_rows,
        "issues": issues,
        "informational": informational,
        "reporting_gaps": reporting_gaps,
        "legacy_frozen": legacy_frozen,
        "success_criteria": success_criteria,
        "swaps": swaps,
        "bundles": bundles,
        "loans": loans,
        "cost_basis": cost_basis,
        "focus_swap_aave_eurc": focus,
        "scope_compare": {
            "summary": scope_compare.get("summary"),
            "legacy_user_vault_positions": scope_compare.get("legacy_user_vault_positions"),
        },
        "pe_scope": pe.to_dict(),
        "recommended_actions": {},
        "prepare_fixes": prepare_fixes,
    }
    report["recommended_actions"] = _classify_recommendations(report, frozen_scope=frozen_scope)

    if prepare_fixes:
        report["proposed_safe_fixes"] = [
            {
                **item,
                "dry_run_command": (
                    f"python3 -m scripts.swap_session_maintenance --swap-id {item['swap_id']}"
                ),
            }
            for item in report["recommended_actions"]["safe_auto"]
            if item.get("swap_id")
        ]

    return report
