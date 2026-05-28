#!/usr/bin/env python3
"""Complète les legs bundle LI.FI pending (mock) + vérifie allocation en base."""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv

load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

os.environ.setdefault("BUNDLE_EXECUTION_PROVIDER", "lifi_base")
os.environ.setdefault("LIFI_SWAPS_MOCK", "1")
os.environ.setdefault("LIFI_SWAPS_ENABLED", "1")

from sqlalchemy import text

from database import SessionLocal
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.portfolio_engine.bundle_execution.bundle_lifi_api import leg_from_swap_audit
from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import BundleLifiLegService
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio


def snapshot(db, *, client_id: UUID, person_id: UUID, portfolio_id: UUID) -> dict:
    privy = db.execute(
        text(
            "SELECT COALESCE(SUM(balance),0) FROM person_wallet_balances "
            "WHERE person_id=:p AND asset='USDC'"
        ),
        {"p": str(person_id)},
    ).scalar()

    direct = db.execute(
        text(
            """
            SELECT COALESCE(SUM(pa.quantity),0)
            FROM pe_position_atoms pa
            JOIN pe_portfolios pf ON pf.id=pa.portfolio_id
            JOIN pe_instruments i ON i.id=pa.instrument_id
            JOIN pe_assets a ON a.id=i.asset_id
            WHERE pf.client_id=:c AND pf.portfolio_type='direct_portfolio'
              AND pa.position_type='spot' AND pa.status='open' AND a.symbol='USDC'
            """
        ),
        {"c": str(client_id)},
    ).scalar()

    cash = db.execute(
        text(
            """
            SELECT COALESCE(SUM(pa.quantity),0)
            FROM pe_position_atoms pa
            JOIN pe_instruments i ON i.id=pa.instrument_id
            JOIN pe_assets a ON a.id=i.asset_id
            WHERE pa.portfolio_id=:p AND pa.position_type='cash'
              AND pa.status='open' AND a.symbol='USDC'
            """
        ),
        {"p": str(portfolio_id)},
    ).scalar()

    spots = db.execute(
        text(
            """
            SELECT a.symbol, pa.position_type, pa.quantity::text
            FROM pe_position_atoms pa
            JOIN pe_instruments i ON i.id=pa.instrument_id
            JOIN pe_assets a ON a.id=i.asset_id
            WHERE pa.portfolio_id=:p AND pa.status='open' AND pa.position_type='spot'
            ORDER BY a.symbol
            """
        ),
        {"p": str(portfolio_id)},
    ).fetchall()

    privy_assets = db.execute(
        text(
            """
            SELECT asset, balance::text FROM person_wallet_balances
            WHERE person_id=:p AND balance > 0 ORDER BY asset
            """
        ),
        {"p": str(person_id)},
    ).fetchall()

    swaps = db.execute(
        text(
            """
            SELECT from_asset, to_asset, amount_in::text, status
            FROM person_wallet_swaps WHERE person_id=:p ORDER BY created_at
            """
        ),
        {"p": str(person_id)},
    ).fetchall()

    lock = db.execute(
        text("SELECT metadata->'bundle_invest_lock' FROM pe_portfolios WHERE id=:p"),
        {"p": str(portfolio_id)},
    ).scalar()

    return {
        "privy_usdc": float(Decimal(str(privy or 0))),
        "direct_usdc": float(Decimal(str(direct or 0))),
        "bundle_cash_usdc": float(Decimal(str(cash or 0))),
        "bundle_spots": [{"asset": r[0], "type": r[1], "qty": r[2]} for r in spots],
        "privy_balances": {r[0]: r[1] for r in privy_assets},
        "swaps": [{"from": r[0], "to": r[1], "in": r[2], "status": r[3]} for r in swaps],
        "lock": lock,
    }


def main() -> None:
    batch_id = os.environ.get("BATCH_ID", "054b139a-09b0-409e-93ff-3182f0c2b729")
    portfolio_id = UUID(os.environ.get("PORTFOLIO_ID", "5607e764-dec3-427e-8a88-0c41ff38d61c"))
    client_email = os.environ.get("CLIENT_EMAIL", "gaelitier@gmail.com")

    db = SessionLocal()
    svc = BundleLifiLegService()
    repo = PersonWalletSwapRepository()

    try:
        client = db.query(Client).filter(Client.email.ilike(client_email)).first()
        if client is None or client.person_id is None:
            raise SystemExit("client/person introuvable")

        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise SystemExit("portfolio introuvable")

        before = snapshot(
            db, client_id=client.id, person_id=client.person_id, portfolio_id=portfolio_id,
        )
        print("=== AVANT COMPLÉTION LEGS ===")
        print(json.dumps(before, indent=2))

        swaps = (
            db.execute(
                text(
                    """
                    SELECT id FROM person_wallet_swaps
                    WHERE person_id = :p
                      AND status NOT IN ('CONFIRMED', 'FAILED', 'EXPIRED')
                    ORDER BY created_at
                    """
                ),
                {"p": str(client.person_id)},
            )
            .fetchall()
        )
        pending = [repo.get_for_person(db, swap_id=row[0], person_id=client.person_id) for row in swaps]
        pending = [s for s in pending if s is not None]
        print(f"\nPending swaps: {len(pending)}")

        results = []
        for i, swap in enumerate(pending):
            leg = leg_from_swap_audit(swap)
            if leg is None:
                print(f"SKIP swap {swap.id}: no leg context")
                continue
            tx_hash = f"0xmock-complete-{batch_id[:8]}-{i}"
            print(f"Submit leg {swap.from_asset}->{swap.to_asset} swap={swap.id}")
            out = svc.submit_leg_tx(
                db,
                leg=leg,
                person_id=client.person_id,
                swap_id=swap.id,
                tx_hash=tx_hash,
            )
            db.commit()
            results.append(
                {
                    "swap_id": str(swap.id),
                    "to": swap.to_asset,
                    "status": out.status,
                    "tx_hash": out.tx_hash,
                    "amount_to": str(out.amount_to) if out.amount_to else None,
                }
            )

        print("\n=== LEG RESULTS ===")
        print(json.dumps(results, indent=2))

        entry_instrument_id = None
        lock = before.get("lock") or {}
        if isinstance(lock, dict):
            entry_instrument_id = lock.get("entry_instrument_id")
        if not entry_instrument_id:
            row = db.execute(
                text(
                    "SELECT metadata->'bundle_invest_lock'->>'entry_instrument_id' "
                    "FROM pe_portfolios WHERE id=:p"
                ),
                {"p": str(portfolio_id)},
            ).scalar()
            entry_instrument_id = row

        planned = Decimal(str(lock.get("funding_amount") or before["bundle_cash_usdc"] or 50))
        consumed = sum(
            Decimal(str(r.get("amount_to") or 0)) for r in results if r.get("status") == "completed"
        )
        # entry consumed = sum amount_in from confirmed swaps
        consumed_in = db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount_in),0) FROM person_wallet_swaps
                WHERE person_id=:p AND status='CONFIRMED' AND from_asset='USDC'
                """
            ),
            {"p": str(client.person_id)},
        ).scalar()
        consumed_in = Decimal(str(consumed_in or 0))

        orch = BundleOrchestrator()
        finalize = orch.finalize_lifi_batch(
            db,
            client_id=client.id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            entry_instrument_id=UUID(str(entry_instrument_id)),
            planned_entry_total=planned,
            entry_consumed=consumed_in,
        )
        db.commit()
        print("\n=== FINALIZE ===")
        print(json.dumps(finalize, indent=2, default=str))

        after = snapshot(
            db, client_id=client.id, person_id=client.person_id, portfolio_id=portfolio_id,
        )
        print("\n=== APRÈS COMPLÉTION ===")
        print(json.dumps(after, indent=2))

        checks = []
        checks.append(("all legs completed", all(r["status"] == "completed" for r in results)))
        checks.append(("bundle cash leg near zero", after["bundle_cash_usdc"] < 0.01))
        checks.append(("bundle spot atoms present", len(after["bundle_spots"]) >= 5))
        checks.append(
            ("privy USDC decreased",
             after["privy_usdc"] < before["privy_usdc"] - 49),
        )
        checks.append(
            ("accounting USDC: direct+cash≈privy",
             abs((after["direct_usdc"] + after["bundle_cash_usdc"]) - after["privy_usdc"]) < 0.02),
        )
        checks.append(("invest lock cleared", after["lock"] is None))

        print("\n=== CHECKS ===")
        ok = True
        for label, passed in checks:
            print(f"  [{'OK' if passed else 'FAIL'}] {label}")
            ok = ok and passed

        if ok:
            print("\nVERIFY_ALLOCATION_COMPLETE_OK")
        else:
            raise SystemExit(1)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
