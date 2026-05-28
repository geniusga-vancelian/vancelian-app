#!/usr/bin/env python3
"""Vérifie le modèle fund-first : self-trading → cash leg, Privy inchangé (legs pending).

Usage (api/, uvicorn local + DB arquantix_fresh) :
  python3 scripts/verify_bundle_fund_first_local.py [--amount 50] [--client-email gaelitier@gmail.com]
"""
from __future__ import annotations

import argparse
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

# Pas d'auto-complete mock : on veut voir l'état post-fund, pre-allocation on-chain
os.environ["BUNDLE_EXECUTION_PROVIDER"] = "lifi_base"
os.environ["LIFI_SWAPS_MOCK"] = "1"
os.environ["LIFI_SWAPS_ENABLED"] = "1"
os.environ["BUNDLE_LIFI_SYNC_MOCK"] = "0"

from sqlalchemy import text

from database import SessionLocal
from services.portfolio_engine.bundle_execution import BundleExecutionAdapter
from services.portfolio_engine.bundle_execution.lifi_provider import LifiExecutionProvider
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio


def _snapshot(db, *, client_id: UUID, person_id: UUID | None, portfolio_id: UUID) -> dict:
    privy_usdc = Decimal("0")
    if person_id:
        row = db.execute(
            text(
                """
                SELECT COALESCE(SUM(balance), 0) AS total
                FROM person_wallet_balances
                WHERE person_id = :pid AND asset = 'USDC'
                """
            ),
            {"pid": str(person_id)},
        ).fetchone()
        privy_usdc = Decimal(str(row[0] if row else 0))

    direct = db.execute(
        text(
            """
            SELECT COALESCE(SUM(pa.quantity), 0)
            FROM pe_position_atoms pa
            JOIN pe_portfolios pf ON pf.id = pa.portfolio_id
            JOIN pe_instruments i ON i.id = pa.instrument_id
            JOIN pe_assets a ON a.id = i.asset_id
            WHERE pf.client_id = :cid
              AND pf.portfolio_type = 'direct_portfolio'
              AND pa.position_type = 'spot'
              AND pa.status = 'open'
              AND a.symbol = 'USDC'
            """
        ),
        {"cid": str(client_id)},
    ).scalar()

    bundle_cash = db.execute(
        text(
            """
            SELECT COALESCE(SUM(pa.quantity), 0)
            FROM pe_position_atoms pa
            JOIN pe_instruments i ON i.id = pa.instrument_id
            JOIN pe_assets a ON a.id = i.asset_id
            WHERE pa.portfolio_id = :pid
              AND pa.position_type = 'cash'
              AND pa.status = 'open'
              AND a.symbol = 'USDC'
            """
        ),
        {"pid": str(portfolio_id)},
    ).scalar()

    bundle_spots = db.execute(
        text(
            """
            SELECT a.symbol, pa.quantity::text, pa.position_type
            FROM pe_position_atoms pa
            JOIN pe_instruments i ON i.id = pa.instrument_id
            JOIN pe_assets a ON a.id = i.asset_id
            WHERE pa.portfolio_id = :pid AND pa.status = 'open'
            ORDER BY pa.position_type, a.symbol
            """
        ),
        {"pid": str(portfolio_id)},
    ).fetchall()

    lock = db.execute(
        text("SELECT metadata->'bundle_invest_lock' FROM pe_portfolios WHERE id = :pid"),
        {"pid": str(portfolio_id)},
    ).scalar()

    pending_swaps = 0
    if person_id:
        pending_swaps = db.execute(
            text(
                """
                SELECT COUNT(*) FROM person_wallet_swaps
                WHERE person_id = :pid AND status NOT IN ('confirmed', 'failed', 'expired')
                """
            ),
            {"pid": str(person_id)},
        ).scalar() or 0

    return {
        "privy_usdc": float(privy_usdc),
        "direct_usdc_spot": float(Decimal(str(direct or 0))),
        "bundle_cash_usdc": float(Decimal(str(bundle_cash or 0))),
        "bundle_atoms": [{"asset": r[0], "qty": r[1], "type": r[2]} for r in bundle_spots],
        "bundle_invest_lock": lock,
        "pending_swaps": int(pending_swaps),
    }


def _cleanup_bundle_portfolio(db, portfolio_id: UUID) -> None:
    db.execute(
        text("DELETE FROM pe_position_atoms WHERE portfolio_id = :pid"),
        {"pid": str(portfolio_id)},
    )
    db.execute(
        text(
            """
            UPDATE pe_portfolios
            SET metadata = metadata - 'bundle_invest_lock'
            WHERE id = :pid
            """
        ),
        {"pid": str(portfolio_id)},
    )
    db.execute(text("DELETE FROM person_wallet_swaps"))
    db.execute(
        text(
            """
            DELETE FROM transaction_intents
            WHERE product_type IN ('bundle_invest', 'lifi_swap')
               OR linked_table IN ('bundle_invest_lock', 'person_wallet_swaps')
            """
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amount", type=float, default=50.0)
    parser.add_argument("--client-email", default="gaelitier@gmail.com")
    parser.add_argument("--portfolio-id", default="5607e764-dec3-427e-8a88-0c41ff38d61c")
    parser.add_argument("--skip-cleanup", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        client = (
            db.query(Client)
            .filter(Client.email.ilike(args.client_email))
            .first()
        )
        if client is None:
            raise SystemExit(f"Client introuvable: {args.client_email}")

        portfolio = db.query(Portfolio).filter(Portfolio.id == UUID(args.portfolio_id)).first()
        if portfolio is None or portfolio.client_id != client.id:
            raise SystemExit("Portfolio bundle introuvable ou client mismatch")

        print("=== CONFIG ===")
        print(f"client_id={client.id}")
        print(f"person_id={client.person_id}")
        print(f"portfolio_id={portfolio.id} ({portfolio.name})")
        print(f"amount={args.amount} USDC")
        print(f"BUNDLE_LIFI_SYNC_MOCK={os.environ.get('BUNDLE_LIFI_SYNC_MOCK')}")

        if not args.skip_cleanup:
            print("\n=== CLEANUP bundle (Privy conservé) ===")
            _cleanup_bundle_portfolio(db, portfolio.id)
            db.commit()

        before = _snapshot(
            db,
            client_id=client.id,
            person_id=client.person_id,
            portfolio_id=portfolio.id,
        )
        print("\n=== AVANT INVEST ===")
        print(json.dumps(before, indent=2, default=str))

        if before["privy_usdc"] < args.amount:
            raise SystemExit(
                f"Privy USDC insuffisant ({before['privy_usdc']} < {args.amount}). "
                "Simulez un dépôt admin Base avant le test."
            )

        adapter = BundleExecutionAdapter(provider=LifiExecutionProvider())
        orch = BundleOrchestrator(execution_adapter=adapter)
        result = orch.invest_into_bundle(
            db,
            client_id=client.id,
            portfolio_id=portfolio.id,
            funding_asset="USDC",
            funding_amount=Decimal(str(args.amount)),
        )
        db.commit()

        after = _snapshot(
            db,
            client_id=client.id,
            person_id=client.person_id,
            portfolio_id=portfolio.id,
        )

        print("\n=== RÉSULTAT INVEST ===")
        print(json.dumps(result, indent=2, default=str))
        print("\n=== APRÈS INVEST ===")
        print(json.dumps(after, indent=2, default=str))

        print("\n=== VÉRIFICATIONS FUND-FIRST ===")
        privy_delta = after["privy_usdc"] - before["privy_usdc"]
        direct_delta = after["direct_usdc_spot"] - before["direct_usdc_spot"]
        cash_delta = after["bundle_cash_usdc"] - before["bundle_cash_usdc"]

        checks = [
            (
                "fund action",
                result.get("funding", {}).get("action") == "fund_cash_leg_from_self_trading",
                result.get("funding", {}).get("action"),
            ),
            (
                "privy inchangé au fund (sync mock off)",
                abs(privy_delta) < 0.0001,
                f"delta={privy_delta}",
            ),
            (
                "cash leg crédité",
                abs(cash_delta - args.amount) < 0.0001,
                f"cash_delta={cash_delta}",
            ),
            (
                "direct USDC débité",
                abs(direct_delta + args.amount) < 0.0001
                or (before["direct_usdc_spot"] == 0 and after["direct_usdc_spot"] == 0 and cash_delta == args.amount),
                f"direct_delta={direct_delta} (bootstrap Privy→direct puis débit)",
            ),
            (
                "legs pending (pas d'allocation auto)",
                result.get("status") in ("pending_signature", "partial_pending"),
                result.get("status"),
            ),
        ]
        ok = True
        for label, passed, detail in checks:
            mark = "OK" if passed else "FAIL"
            print(f"  [{mark}] {label}: {detail}")
            ok = ok and passed

        if ok:
            print("\nVERIFY_FUND_FIRST_OK")
        else:
            print("\nVERIFY_FUND_FIRST_PARTIAL — voir détails ci-dessus")
            raise SystemExit(1)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
