#!/usr/bin/env python3
"""Test E2E complet fund-first + allocation mock — boucle jusqu'à succès."""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv

load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

os.environ["BUNDLE_EXECUTION_PROVIDER"] = "lifi_base"
os.environ["LIFI_SWAPS_MOCK"] = "1"
os.environ["LIFI_SWAPS_ENABLED"] = "1"

from sqlalchemy import text

from database import SessionLocal
from services.portfolio_engine.bundle_execution import BundleExecutionAdapter
from services.portfolio_engine.bundle_execution.bundle_lifi_api import leg_from_swap_audit
from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import BundleLifiLegService
from services.portfolio_engine.bundle_execution.lifi_provider import LifiExecutionProvider
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio
from services.lifi.swap_repository import PersonWalletSwapRepository


CLIENT_EMAIL = "gaelitier@gmail.com"
PORTFOLIO_ID = UUID("5607e764-dec3-427e-8a88-0c41ff38d61c")
AMOUNT = Decimal("30")


def cleanup_bundle(db, portfolio_id: UUID) -> None:
    db.execute(text("DELETE FROM pe_position_atoms WHERE portfolio_id = :p"), {"p": str(portfolio_id)})
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
    db.execute(
        text("UPDATE pe_portfolios SET metadata = metadata - 'bundle_invest_lock' WHERE id = :p"),
        {"p": str(portfolio_id)},
    )
    # Remettre direct USDC = privy (réalignement comptable self-trading)
    db.execute(
        text(
            """
            DELETE FROM pe_position_atoms pa
            USING pe_portfolios pf, pe_instruments i, pe_assets a
            WHERE pa.portfolio_id = pf.id
              AND pf.portfolio_type = 'direct_portfolio'
              AND pa.instrument_id = i.id AND i.asset_id = a.id
              AND a.symbol = 'USDC' AND pa.position_type = 'spot'
            """
        )
    )


def snap(db, client_id, person_id, portfolio_id):
    privy = float(
        db.execute(
            text("SELECT COALESCE(SUM(balance),0) FROM person_wallet_balances WHERE person_id=:p AND asset='USDC'"),
            {"p": str(person_id)},
        ).scalar()
    )
    direct = float(
        db.execute(
            text(
                """
                SELECT COALESCE(SUM(pa.quantity),0)
                FROM pe_position_atoms pa JOIN pe_portfolios pf ON pf.id=pa.portfolio_id
                JOIN pe_instruments i ON i.id=pa.instrument_id JOIN pe_assets a ON a.id=i.asset_id
                WHERE pf.client_id=:c AND pf.portfolio_type='direct_portfolio'
                  AND pa.position_type='spot' AND a.symbol='USDC' AND pa.status='open'
                """
            ),
            {"c": str(client_id)},
        ).scalar()
    )
    cash = float(
        db.execute(
            text(
                """
                SELECT COALESCE(SUM(pa.quantity),0)
                FROM pe_position_atoms pa JOIN pe_instruments i ON i.id=pa.instrument_id
                JOIN pe_assets a ON a.id=i.asset_id
                WHERE pa.portfolio_id=:p AND pa.position_type='cash' AND a.symbol='USDC'
                """
            ),
            {"p": str(portfolio_id)},
        ).scalar()
    )
    spots = db.execute(
        text(
            """
            SELECT a.symbol, pa.quantity::float
            FROM pe_position_atoms pa JOIN pe_instruments i ON i.id=pa.instrument_id
            JOIN pe_assets a ON a.id=i.asset_id
            WHERE pa.portfolio_id=:p AND pa.position_type='spot' AND pa.status='open'
            ORDER BY a.symbol
            """
        ),
        {"p": str(portfolio_id)},
    ).fetchall()
    return {
        "privy_usdc": privy,
        "direct_usdc": direct,
        "bundle_cash_usdc": cash,
        "bundle_spots": {r[0]: r[1] for r in spots},
    }


def main():
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.email.ilike(CLIENT_EMAIL)).first()
        portfolio = db.query(Portfolio).filter(Portfolio.id == PORTFOLIO_ID).first()
        assert client and portfolio and client.person_id

        print("=== E2E FUND-FIRST + ALLOCATION MOCK ===")
        cleanup_bundle(db, PORTFOLIO_ID)
        db.commit()

        # Réaligner direct depuis privy
        from services.portfolio_engine.bundle_execution.bundle_funding import (
            sync_self_trading_atom_from_custody,
        )
        from services.portfolio_engine.instruments.models import Instrument
        from services.portfolio_engine.assets.models import Asset

        usdc_asset = db.query(Asset).filter(Asset.symbol == "USDC").first()
        usdc_instr = (
            db.query(Instrument)
            .filter(Instrument.asset_id == usdc_asset.id, Instrument.instrument_type == "spot")
            .first()
        )
        sync_self_trading_atom_from_custody(
            db,
            client_id=client.id,
            person_id=client.person_id,
            entry_asset="USDC",
            entry_instrument_id=usdc_instr.id,
        )
        db.commit()

        s0 = snap(db, client.id, client.person_id, PORTFOLIO_ID)
        print("START:", json.dumps(s0))

        os.environ["BUNDLE_LIFI_SYNC_MOCK"] = "0"
        adapter = BundleExecutionAdapter(provider=LifiExecutionProvider())
        orch = BundleOrchestrator(execution_adapter=adapter)
        invest = orch.invest_into_bundle(
            db,
            client_id=client.id,
            portfolio_id=PORTFOLIO_ID,
            funding_asset="USDC",
            funding_amount=AMOUNT,
        )
        db.commit()

        s1 = snap(db, client.id, client.person_id, PORTFOLIO_ID)
        print("AFTER FUND:", json.dumps(s1))
        print("INVEST STATUS:", invest["status"])

        assert invest["funding"]["action"] == "fund_cash_leg_from_self_trading"
        assert abs(s1["privy_usdc"] - s0["privy_usdc"]) < 0.001, "Privy must not move at fund"
        assert abs(s1["bundle_cash_usdc"] - float(AMOUNT)) < 0.001, "Cash leg must equal funded amount"

        # Complete legs
        svc = BundleLifiLegService()
        repo = PersonWalletSwapRepository()
        rows = db.execute(
            text(
                "SELECT id FROM person_wallet_swaps WHERE person_id=:p AND status != 'CONFIRMED' ORDER BY created_at"
            ),
            {"p": str(client.person_id)},
        ).fetchall()
        for i, (sid,) in enumerate(rows):
            swap = repo.get_for_person(db, swap_id=sid, person_id=client.person_id)
            leg = leg_from_swap_audit(swap)
            svc.submit_leg_tx(
                db, leg=leg, person_id=client.person_id, swap_id=sid,
                tx_hash=f"0xe2e-mock-{i}",
            )
            db.commit()

        entry_iid = invest["entry_instrument_id"]
        consumed = db.execute(
            text(
                "SELECT COALESCE(SUM(amount_in),0) FROM person_wallet_swaps "
                "WHERE person_id=:p AND status='CONFIRMED' AND from_asset='USDC'"
            ),
            {"p": str(client.person_id)},
        ).scalar()
        orch.finalize_lifi_batch(
            db,
            client_id=client.id,
            portfolio_id=PORTFOLIO_ID,
            batch_id=str(invest["batch_id"]),
            entry_instrument_id=UUID(str(entry_iid)),
            planned_entry_total=AMOUNT,
            entry_consumed=Decimal(str(consumed)),
        )
        db.commit()

        s2 = snap(db, client.id, client.person_id, PORTFOLIO_ID)
        print("AFTER ALLOC:", json.dumps(s2))

        inv_e = BundleOrchestrator.check_invariant_e(db, PORTFOLIO_ID)
        print("INVARIANT_E:", json.dumps(inv_e, indent=2, default=str))

        assert s2["bundle_cash_usdc"] < 0.01, "Cash leg should be depleted"
        assert len(s2["bundle_spots"]) >= 5, "Need 5 spot atoms"
        assert s2["privy_usdc"] < s1["privy_usdc"], "Privy USDC must decrease after swaps"
        assert abs(s2["direct_usdc"] + s2["bundle_cash_usdc"] - s2["privy_usdc"]) < 0.02
        assert inv_e.get("invariant_e_ok") is True, f"Invariant E failed: {inv_e}"

        print("\nE2E_FUND_FIRST_ALLOCATION_OK")
    except Exception as exc:
        db.rollback()
        raise SystemExit(f"E2E_FAILED: {exc}") from exc
    finally:
        db.close()


if __name__ == "__main__":
    main()
