"""Audit lecture seule — réconciliation compte crypto multi-couches (Privy / PE / swaps / bundles / loans)."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from config.base_allowed_assets import BASE_ALLOWED_SYMBOLS, BASE_LIFI_CHAIN_ID
from database import Person, PersonExternalIdentity
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
from services.portfolio_engine.internal_scope_movements.pe_reader import read_current_pe_scope_snapshot
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.privy_wallet.deposit_backfill import fetch_aggregated_on_chain_balances
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import PersonCryptoWalletRepository, PersonWalletBalanceRepository

logger = logging.getLogger(__name__)

DUST = Decimal("0.000001")
FOCUS_SWAP_ID = "76830776-039d-48a3-9e58-df48b0b10f7e"


def _fmt(value: Decimal | None) -> str:
    if value is None:
        return "0"
    text = format(Decimal(str(value)).normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


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


def _classify_recommendations(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
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
    for row in report.get("cost_basis", {}).get("missing", []):
        if any(s["swap_id"] == row["swap_id"] for s in report.get("swaps", {}).get("confirmed_incomplete_settlement", [])):
            continue
        review.append({"type": "cost_basis_missing", **row})

    for asset_row in report.get("assets", []):
        delta = Decimal(str(asset_row.get("delta_ledger_vs_onchain") or "0"))
        if abs(delta) > DUST:
            review.append(
                {
                    "type": "ledger_onchain_delta",
                    "asset": asset_row["asset"],
                    "delta": asset_row["delta_ledger_vs_onchain"],
                }
            )
        for issue in asset_row.get("issues", []):
            if "collateral" in issue or "bundle" in issue:
                forbidden.append({"type": "scope_overlap", "asset": asset_row["asset"], "issue": issue})
            elif "debt" in issue:
                forbidden.append({"type": "active_liability", "asset": asset_row["asset"], "issue": issue})

    for gap in report.get("bundles", {}).get("mismatches", []):
        review.append({"type": "bundle_mismatch", **gap})

    return {"safe_auto": safe, "requires_review": review, "do_not_auto_fix": forbidden}


def build_person_crypto_audit(
    db: Session,
    *,
    email: str,
    prepare_fixes: bool = False,
) -> dict[str, Any]:
    """Audit lecture seule. ``prepare_fixes`` liste les correctifs safe sans écrire."""
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

    on_chain: dict[str, Decimal] = {}
    if primary_wallet and primary_wallet.address:
        assets = sorted(set(BASE_ALLOWED_SYMBOLS) | set(ledger.keys()))
        raw = fetch_aggregated_on_chain_balances(
            wallet_address=primary_wallet.address,
            chain_ids=[BASE_LIFI_CHAIN_ID],
            assets=list(assets),
        )
        for (_cid, asset), bal in raw.items():
            on_chain[asset] = bal

    asset_rows: list[dict[str, Any]] = []
    all_assets = sorted(set(ledger.keys()) | set(on_chain.keys()) | set(pe.trading_available.keys()))

    for asset in all_assets:
        ledger_bal = ledger.get(asset, Decimal("0"))
        chain_bal = on_chain.get(asset, Decimal("0"))
        direct_avail = pe.trading_available.get(asset, Decimal("0"))
        bundle_alloc = pe.bundle_cash.get(asset, Decimal("0")) + pe.bundle_position.get(asset, Decimal("0"))
        collateral = pe.trading_locked_collateral.get(asset, Decimal("0"))
        debt = pe.liability.get(asset, Decimal("0"))
        ledger_spendable = max(ledger_bal - collateral, Decimal("0"))
        swappable = min(chain_bal, ledger_spendable) if chain_bal > 0 else ledger_spendable
        delta = ledger_bal - chain_bal
        issues: list[str] = []
        if abs(delta) > DUST:
            if delta > 0:
                issues.append("ledger_gt_onchain")
            else:
                issues.append("ledger_lt_onchain")
        if chain_bal > DUST and ledger_bal <= DUST:
            issues.append("onchain_without_ledger")
        if ledger_bal > DUST and chain_bal <= DUST and collateral <= DUST and bundle_alloc <= DUST:
            issues.append("ledger_without_onchain")
        if collateral > DUST and direct_avail > DUST:
            issues.append("collateral_and_direct_available_overlap")
        if debt > DUST:
            issues.append("active_debt_usdc")
        if bundle_alloc > DUST and ledger_bal > DUST:
            issues.append("bundle_and_ledger_both_nonzero")

        asset_rows.append(
            {
                "asset": asset,
                "on_chain_balance": _fmt(chain_bal),
                "ledger_balance": _fmt(ledger_bal),
                "direct_available": _fmt(direct_avail),
                "bundle_allocated": _fmt(bundle_alloc),
                "collateral_locked": _fmt(collateral),
                "debt": _fmt(debt),
                "swappable_balance": _fmt(swappable),
                "delta_ledger_vs_onchain": _fmt(delta),
                "issues": issues,
            }
        )

    swaps = _swap_issues(db, person_id)
    bundles = _bundle_positions(db, person_id)
    cost_basis = _cost_basis_audit(db, person_id)
    focus = _focus_swap(db, FOCUS_SWAP_ID)

    loans = {
        "positions": [
            {"asset": k, "locked_collateral": _fmt(v)}
            for k, v in sorted(pe.trading_locked_collateral.items())
        ],
        "liabilities": [{"asset": k, "amount": _fmt(v)} for k, v in sorted(pe.liability.items())],
        "mismatches": [],
    }

    report: dict[str, Any] = {
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
            "physical_truth": "wallet_privy_on_chain",
            "application_truth": "person_wallet_balances_reconcilable",
            "bundle_scope": "economic_sub_ledger_not_separate_wallet",
            "collateral_scope": "locked_non_spendable",
            "swappable_formula": "min(on_chain_wallet_balance, ledger_balance - collateral_locked)",
        },
        "assets": asset_rows,
        "swaps": swaps,
        "bundles": bundles,
        "loans": loans,
        "cost_basis": cost_basis,
        "focus_swap_aave_eurc": focus,
        "pe_scope": pe.to_dict(),
        "recommended_actions": {},
        "prepare_fixes": prepare_fixes,
    }
    report["recommended_actions"] = _classify_recommendations(report)

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
