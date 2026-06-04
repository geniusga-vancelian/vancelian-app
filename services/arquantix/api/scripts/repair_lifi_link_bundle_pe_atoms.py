#!/usr/bin/env python3
"""Répare les atoms PE bundle LINK gonflés (8d vs 18d on-chain)."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID


def _bootstrap() -> None:
    api_dir = Path(__file__).resolve().parent.parent
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))
    os.chdir(api_dir)


INFLATION = Decimal("1000")
MIN_QTY = Decimal("1000")


def main() -> None:
    _bootstrap()
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry_run = not args.apply

    import main as _main  # noqa: F401

    from database import SessionLocal
    from services.cost_basis.ingest_bundle_lifi import ingest_bundle_lifi_swap_settlement
    from services.cost_basis.models import CostBasisExecution
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.lifi_actual_receive import _resolve_swap_wallet
    from services.lifi.models import PersonWalletSwap
    from services.portfolio_engine.assets.models import Asset
    from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
        bundle_context_for_swap,
        bundle_portfolio_id_from_swap,
        is_bundle_internal_swap,
    )
    from services.portfolio_engine.instruments.models import Instrument
    from services.portfolio_engine.positions.models import PositionAtom

    db = SessionLocal()
    try:
        swaps = (
            db.query(PersonWalletSwap)
            .filter(
                PersonWalletSwap.status == SwapSessionStatus.CONFIRMED.value,
                PersonWalletSwap.to_asset == "LINK",
            )
            .order_by(PersonWalletSwap.updated_at.desc())
            .limit(200)
            .all()
        )
        rows = (
            db.query(PositionAtom, Asset, Instrument)
            .join(Instrument, Instrument.id == PositionAtom.instrument_id)
            .join(Asset, Asset.id == Instrument.asset_id)
            .filter(Asset.symbol == "LINK", PositionAtom.status == "open")
            .all()
        )
        print(f"Mode: {'DRY_RUN' if dry_run else 'APPLY'}")
        repaired = 0
        for atom, _a, _i in rows:
            qty = Decimal(str(atom.quantity or 0))
            if qty < MIN_QTY:
                continue
            portfolio_id = atom.portfolio_id
            matched = None
            for candidate in swaps:
                if not is_bundle_internal_swap(candidate):
                    continue
                pid_raw = bundle_portfolio_id_from_swap(candidate)
                pid = UUID(str(pid_raw)) if pid_raw else None
                if pid is None:
                    ctx = bundle_context_for_swap(candidate) or {}
                    raw = ctx.get("portfolio_id")
                    pid = UUID(str(raw)) if raw else None
                if pid != portfolio_id:
                    continue
                est = Decimal(str(candidate.estimated_receive or 0))
                if est <= 0 or qty / est < INFLATION:
                    continue
                matched = candidate
                break
            if matched is None:
                print(f"  skip atom={atom.id} portfolio={portfolio_id} qty={qty} (no swap)")
                continue
            correct = Decimal(str(matched.estimated_receive))
            wrong = qty
            print(
                f"  atom={atom.id} portfolio={portfolio_id} swap={matched.id} "
                f"wrong={wrong} -> correct={correct}"
            )
            if dry_run:
                repaired += 1
                continue
            old_cb = Decimal(str(atom.cost_basis or 0))
            new_cb = (old_cb * correct / wrong).quantize(Decimal("0.00000001")) if wrong > 0 else old_cb
            atom.quantity = correct
            atom.available_quantity = correct
            atom.cost_basis = new_cb
            if correct > 0:
                atom.average_entry_price = new_cb / correct
            meta = dict(atom.metadata_ or {})
            meta["decimal_repair_v1"] = {
                "repaired_at": datetime.now(timezone.utc).isoformat(),
                "swap_id": str(matched.id),
                "wrong_qty": str(wrong),
                "correct_qty": str(correct),
            }
            atom.metadata_ = meta
            db.add(atom)
            prefix = f"bundle-lifi:{matched.id}:"
            for row in (
                db.query(CostBasisExecution)
                .filter(CostBasisExecution.provider_source == "bundle_lifi")
                .filter(CostBasisExecution.provider_execution_id.like(f"{prefix}%"))
                .all()
            ):
                db.delete(row)
            db.flush()
            wallet = _resolve_swap_wallet(db, matched)
            ingest_bundle_lifi_swap_settlement(
                db, matched, wallet=wallet, amount_out=correct, portfolio_id=portfolio_id,
            )
            repaired += 1
        print(f"Repaired atoms: {repaired}")
        if not dry_run and repaired:
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
