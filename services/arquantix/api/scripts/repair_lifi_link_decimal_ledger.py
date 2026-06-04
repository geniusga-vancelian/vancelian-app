#!/usr/bin/env python3
"""
Répare les crédits ledger LINK gonflés par parsing ERC-20 avec 8 décimales au lieu de 18
(règlement swap LI.FI, source on_chain_erc20_transfer).

Stratégie par dépôt affecté :
  1. void du crédit gonflé (person_wallet_deposits + balance)
  2. recréation du crédit avec le montant ``swap_amount_to_estimated`` (devis LI.FI)
  3. suppression + ré-ingestion cost_basis_executions pour le swap (idempotent)

Usage (depuis services/arquantix/api, DATABASE_URL requis) ::
  python3 scripts/repair_lifi_link_decimal_ledger.py --dry-run
  python3 scripts/repair_lifi_link_decimal_ledger.py --apply
  python3 scripts/repair_lifi_link_decimal_ledger.py --apply --person-id <UUID>
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID


def _ensure_api_path() -> None:
    api_dir = Path(__file__).resolve().parent.parent
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))
    os.chdir(api_dir)
    try:
        from dotenv import load_dotenv

        for p in (api_dir / ".env.local", api_dir / ".env"):
            if p.exists():
                load_dotenv(p)
                break
    except ImportError:
        pass


INFLATION_RATIO = Decimal("1000")
MIN_INFLATED_ATOM_QTY = Decimal("1000")


def _dec(v: object) -> Decimal | None:
    if v is None:
        return None
    try:
        d = Decimal(str(v))
        return d if d > 0 else None
    except Exception:
        return None


def _find_inflated_link_credits(db, *, person_id: UUID | None):
    from services.privy_wallet.enums import PersonWalletDepositStatus, PersonWalletDirection
    from services.privy_wallet.models import PersonWalletDeposit

    q = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.asset == "LINK",
            PersonWalletDeposit.direction == PersonWalletDirection.CREDIT.value,
            PersonWalletDeposit.status == PersonWalletDepositStatus.CONFIRMED.value,
            PersonWalletDeposit.transaction_kind == "crypto_swap",
        )
        .order_by(PersonWalletDeposit.confirmed_at.desc())
    )
    if person_id is not None:
        q = q.filter(PersonWalletDeposit.person_id == person_id)

    from services.lifi.models import PersonWalletSwap

    inflated = []
    for row in q.limit(500).all():
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        amount = _dec(row.amount)
        if amount is None:
            continue
        estimated = _dec(meta.get("swap_amount_to_estimated"))
        swap_id_raw = str(meta.get("swap_id") or "").strip()
        source = str(meta.get("actual_receive_source") or meta.get("source") or "")

        if estimated is None and swap_id_raw:
            try:
                swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == UUID(swap_id_raw)).first()
                if swap is not None:
                    estimated = _dec(swap.estimated_receive)
            except ValueError:
                swap = None

        if estimated is None:
            if amount >= Decimal("1000") and "lifi" in source.lower():
                estimated = amount / INFLATION_RATIO
            else:
                continue

        if amount / estimated < INFLATION_RATIO:
            continue

        inflated.append(
            {
                "deposit": row,
                "amount": amount,
                "estimated": estimated,
                "swap_id": swap_id_raw,
                "source": source,
            }
        )
    return inflated


def _find_inflated_bundle_link_atoms(db, *, person_id: UUID | None):
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.models import PersonWalletSwap
    from services.portfolio_engine.assets.models import Asset
    from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
        bundle_context_for_swap,
        bundle_portfolio_id_from_swap,
        is_bundle_internal_swap,
    )
    from services.portfolio_engine.instruments.models import Instrument
    from services.portfolio_engine.positions.models import PositionAtom

    rows = (
        db.query(PositionAtom, Asset, Instrument)
        .join(Instrument, Instrument.id == PositionAtom.instrument_id)
        .join(Asset, Asset.id == Instrument.asset_id)
        .filter(Asset.symbol == "LINK", PositionAtom.status == "open")
        .all()
    )
    inflated_atoms = []
    for atom, _asset, _instrument in rows:
        qty = _dec(atom.quantity)
        if qty is None or qty < MIN_INFLATED_ATOM_QTY:
            continue
        portfolio_id = atom.portfolio_id
        swap = (
            db.query(PersonWalletSwap)
            .filter(
                PersonWalletSwap.status == SwapSessionStatus.CONFIRMED.value,
                PersonWalletSwap.to_asset == "LINK",
            )
            .order_by(PersonWalletSwap.updated_at.desc())
            .limit(200)
            .all()
        )
        matched = None
        for candidate in swap:
            if person_id is not None and candidate.person_id != person_id:
                continue
            if not is_bundle_internal_swap(candidate):
                continue
            pid_raw = bundle_portfolio_id_from_swap(candidate)
            pid = UUID(str(pid_raw)) if pid_raw else None
            if pid is not None and pid == portfolio_id:
                matched = candidate
                break
        if matched is None:
            ctx_portfolio = None
            for candidate in swap:
                if person_id is not None and candidate.person_id != person_id:
                    continue
                ctx = bundle_context_for_swap(candidate) or {}
                raw_pid = ctx.get("portfolio_id")
                if raw_pid and UUID(str(raw_pid)) == portfolio_id:
                    matched = candidate
                    break
        if matched is None:
            continue
        est = _dec(matched.estimated_receive)
        if est is None or qty / est < INFLATION_RATIO:
            continue
        inflated_atoms.append(
            {
                "atom": atom,
                "quantity": qty,
                "estimated": est,
                "swap": matched,
                "portfolio_id": portfolio_id,
            }
        )
    return inflated_atoms


def _repair_bundle_link_atom(db, item: dict, *, dry_run: bool) -> dict:
    from services.cost_basis.ingest_bundle_lifi import ingest_bundle_lifi_swap_settlement
    from services.cost_basis.models import CostBasisExecution
    from services.lifi.lifi_actual_receive import _resolve_swap_wallet

    atom = item["atom"]
    swap = item["swap"]
    wrong = item["quantity"]
    correct = item["estimated"]
    portfolio_id = item["portfolio_id"]

    result = {
        "atom_id": str(atom.id),
        "portfolio_id": str(portfolio_id),
        "swap_id": str(swap.id),
        "wrong_qty": str(wrong),
        "correct_qty": str(correct),
        "cost_basis_rows_deleted": 0,
        "atom_updated": False,
    }

    prefix = f"bundle-lifi:{swap.id}:"
    cb_rows = (
        db.query(CostBasisExecution)
        .filter(CostBasisExecution.provider_source == "bundle_lifi")
        .filter(CostBasisExecution.provider_execution_id.like(f"{prefix}%"))
        .all()
    )
    result["cost_basis_rows_deleted"] = len(cb_rows)

    if dry_run:
        return result

    old_cb = Decimal(str(atom.cost_basis or 0))
    if wrong > 0 and old_cb > 0:
        new_cb = (old_cb * correct / wrong).quantize(Decimal("0.00000001"))
    else:
        new_cb = old_cb

    atom.quantity = correct
    atom.available_quantity = correct
    atom.cost_basis = new_cb
    if correct > 0:
        atom.average_entry_price = new_cb / correct
    meta = dict(atom.metadata_ or {})
    meta["decimal_repair_v1"] = {
        "repaired_at": datetime.now(timezone.utc).isoformat(),
        "swap_id": str(swap.id),
        "wrong_qty": str(wrong),
        "correct_qty": str(correct),
    }
    atom.metadata_ = meta
    db.add(atom)
    db.flush()
    result["atom_updated"] = True

    for row in cb_rows:
        db.delete(row)
    db.flush()

    wallet = _resolve_swap_wallet(db, swap)
    ingest_bundle_lifi_swap_settlement(
        db,
        swap,
        wallet=wallet,
        amount_out=correct,
        portfolio_id=portfolio_id,
    )
    return result


def _repair_cost_basis_for_swap(db, swap, *, correct_amount_out: Decimal, dry_run: bool) -> int:
    from services.cost_basis.ingest_lifi import ingest_lifi_swap_settlement
    from services.cost_basis.models import CostBasisExecution
    from services.lifi.models import PersonWalletSwap
    from services.lifi.lifi_actual_receive import _resolve_swap_wallet

    swap_row = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap.id).first()
    if swap_row is None:
        return 0

    prefix = f"lifi:{swap.id}:"
    rows = (
        db.query(CostBasisExecution)
        .filter(CostBasisExecution.provider_source == "lifi")
        .filter(CostBasisExecution.provider_execution_id.like(f"{prefix}%"))
        .all()
    )
    deleted = len(rows)
    if dry_run:
        return deleted

    for row in rows:
        db.delete(row)
    db.flush()

    wallet = _resolve_swap_wallet(db, swap_row)
    ingest_lifi_swap_settlement(db, swap_row, wallet=wallet, amount_out=correct_amount_out)
    return deleted


def _apply_repair(db, item: dict, *, dry_run: bool) -> dict:
    from services.lifi.lifi_swap_settlement import _create_swap_ledger_entry, _resolve_swap_wallet
    from services.lifi.models import PersonWalletSwap
    from services.privy_wallet.admin_service import PrivyWalletAdminService
    from services.privy_wallet.enums import PersonWalletDirection
    from services.privy_wallet.models import PersonWalletDeposit
    from services.privy_wallet.schemas import PrivyVoidDepositRequest

    deposit = item["deposit"]
    correct = item["estimated"]
    person_id = deposit.person_id
    swap_id = item["swap_id"]

    result = {
        "deposit_id": str(deposit.id),
        "person_id": str(person_id),
        "swap_id": swap_id,
        "wrong_amount": str(item["amount"]),
        "correct_amount": str(correct),
        "voided": False,
        "credited": False,
        "cost_basis_rows_deleted": 0,
    }

    if dry_run:
        swap = None
        if swap_id:
            swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == UUID(swap_id)).first()
        if swap:
            result["cost_basis_rows_deleted"] = _repair_cost_basis_for_swap(
                db, swap, correct_amount_out=correct, dry_run=True
            )
        return result

    admin = PrivyWalletAdminService()
    admin.void_deposit(
        db,
        PrivyVoidDepositRequest(
            person_id=person_id,
            deposit_id=deposit.id,
            reason="repair_lifi_link_decimal_inflation",
        ),
    )
    result["voided"] = True

    swap = None
    if swap_id:
        try:
            swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == UUID(swap_id)).first()
        except ValueError:
            swap = None

    if swap is not None:
        from services.lifi.lifi_actual_receive import resolve_lifi_actual_receive_amount

        resolved = resolve_lifi_actual_receive_amount(db, swap)
        if resolved is not None and resolved.amount > 0:
            correct = resolved.amount
            result["correct_amount"] = str(correct)
            result["correct_source"] = resolved.source

        wallet = _resolve_swap_wallet(db, swap)
        repair_key = f"lifi-swap:{swap_id}:credit:decimal_repair_v1"
        existing = (
            db.query(PersonWalletDeposit)
            .filter(PersonWalletDeposit.idempotency_key == repair_key)
            .first()
        )
        if existing is None:
            _create_swap_ledger_entry(
                db,
                swap=swap,
                wallet=wallet,
                direction=PersonWalletDirection.CREDIT.value,
                asset="LINK",
                amount=correct,
                chain_id=8453,
                log_index=int((deposit.log_index or 1)) + 1000,
                idempotency_key=repair_key,
                sync_source="lifi_link_decimal_repair",
                settlement_meta={
                    "decimal_repair_v1": True,
                    "repaired_deposit_id": str(deposit.id),
                    "wrong_amount": str(item["amount"]),
                    "actual_receive_source": "swap_amount_to_estimated",
                },
            )
            result["credited"] = True
        result["cost_basis_rows_deleted"] = _repair_cost_basis_for_swap(
            db, swap, correct_amount_out=correct, dry_run=False
        )

    meta = dict(deposit.metadata_json or {})
    meta["decimal_repair_v1"] = {
        "repaired_at": datetime.now(timezone.utc).isoformat(),
        "wrong_amount": str(item["amount"]),
        "correct_amount": str(correct),
        "repair_key": f"lifi-swap:{swap_id}:credit:decimal_repair_v1" if swap_id else None,
    }
    deposit.metadata_json = meta
    db.add(deposit)
    return result


def main() -> None:
    _ensure_api_path()
    parser = argparse.ArgumentParser(description="Repair inflated LINK Li.FI ledger credits")
    parser.add_argument("--dry-run", action="store_true", help="Plan only (default if no --apply)")
    parser.add_argument("--apply", action="store_true", help="Persist repairs")
    parser.add_argument("--person-id", default=None, help="Limit to one person UUID")
    args = parser.parse_args()

    dry_run = not args.apply
    person_id = UUID(args.person_id) if args.person_id else None

    import main  # noqa: F401 — enregistre tous les modèles SQLAlchemy

    from database import SessionLocal

    db = SessionLocal()
    try:
        credit_items = _find_inflated_link_credits(db, person_id=person_id)
        atom_items = _find_inflated_bundle_link_atoms(db, person_id=person_id)
        print(f"Mode: {'DRY_RUN' if dry_run else 'APPLY'}")
        print(f"Inflated LINK swap credits found: {len(credit_items)}")
        print(f"Inflated bundle LINK PE atoms found: {len(atom_items)}")
        if not credit_items and not atom_items:
            print("Nothing to repair.")
            return

        for item in credit_items:
            out = _apply_repair(db, item, dry_run=dry_run)
            print(
                f"  [ledger] deposit={out['deposit_id']} person={out['person_id']} "
                f"swap={out['swap_id']} wrong={out['wrong_amount']} -> correct={out['correct_amount']} "
                f"voided={out['voided']} credited={out['credited']} cb_deleted={out['cost_basis_rows_deleted']}"
            )

        for item in atom_items:
            out = _repair_bundle_link_atom(db, item, dry_run=dry_run)
            print(
                f"  [bundle_pe] atom={out['atom_id']} portfolio={out['portfolio_id']} "
                f"swap={out['swap_id']} wrong={out['wrong_qty']} -> correct={out['correct_qty']} "
                f"atom_updated={out['atom_updated']} cb_deleted={out['cost_basis_rows_deleted']}"
            )

        if not dry_run:
            db.commit()
            print("Committed.")
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
