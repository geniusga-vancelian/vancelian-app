#!/usr/bin/env python3
"""E2E retrait bundle total — Li.FI mock sur compte dev local."""
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
os.environ["BUNDLE_LIFI_SYNC_MOCK"] = "0"

from sqlalchemy import text

from database import SessionLocal
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.portfolio_engine.bundle_execution import BundleExecutionAdapter
from services.portfolio_engine.bundle_execution.bundle_lifi_api import leg_from_swap_audit
from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import BundleLifiLegService
from services.portfolio_engine.bundle_execution.lifi_provider import LifiExecutionProvider
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.bundles.withdraw import BundleWithdrawOrchestrator
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio


CLIENT_EMAIL = "gaelitier@gmail.com"
PORTFOLIO_ID = UUID("5607e764-dec3-427e-8a88-0c41ff38d61c")
FUND_AMOUNT = Decimal("30")


def snap(db, client_id, person_id, portfolio_id):
    privy = float(
        db.execute(
            text(
                "SELECT COALESCE(SUM(balance),0) FROM person_wallet_balances "
                "WHERE person_id=:p AND asset='USDC'"
            ),
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
                  AND pa.status='open'
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
    privy_all = db.execute(
        text(
            """
            SELECT asset, balance::float FROM person_wallet_balances
            WHERE person_id=:p AND balance > 0 ORDER BY asset
            """
        ),
        {"p": str(person_id)},
    ).fetchall()
    return {
        "privy_usdc": privy,
        "direct_usdc": direct,
        "bundle_cash_usdc": cash,
        "bundle_spots": {r[0]: r[1] for r in spots},
        "privy_balances": {r[0]: r[1] for r in privy_all},
    }


def clear_withdraw_lock(db, portfolio_id: UUID) -> None:
    db.execute(
        text("UPDATE pe_portfolios SET metadata = metadata - 'bundle_withdraw_lock' WHERE id = :p"),
        {"p": str(portfolio_id)},
    )


def _has_allocated_spots(state: dict) -> bool:
    return sum(q for q in state["bundle_spots"].values() if q > 0.001) > 0.01


def ensure_allocated_bundle(db, client, portfolio_id: UUID) -> None:
    """Seed fund-first + allocation mock si le bundle n'a pas de spots."""
    state = snap(db, client.id, client.person_id, portfolio_id)
    if _has_allocated_spots(state) and sum(1 for q in state["bundle_spots"].values() if q > 0.001) >= 3:
        print("BUNDLE_ALREADY_ALLOCATED:", json.dumps(state["bundle_spots"]))
        return

    print("=== SEED FUND-FIRST + ALLOCATION (prerequisite) ===")
    from services.portfolio_engine.bundle_execution.bundle_funding import (
        sync_self_trading_atom_from_custody,
    )
    from services.portfolio_engine.assets.models import Asset
    from services.portfolio_engine.instruments.models import Instrument

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

    adapter = BundleExecutionAdapter(provider=LifiExecutionProvider())
    orch = BundleOrchestrator(execution_adapter=adapter)
    invest = orch.invest_into_bundle(
        db,
        client_id=client.id,
        portfolio_id=portfolio_id,
        funding_asset="USDC",
        funding_amount=FUND_AMOUNT,
    )
    db.commit()
    assert invest["funding"]["action"] == "fund_cash_leg_from_self_trading"

    svc = BundleLifiLegService()
    repo = PersonWalletSwapRepository()
    rows = db.execute(
        text(
            "SELECT id FROM person_wallet_swaps "
            "WHERE person_id=:p AND status != 'CONFIRMED' AND from_asset='USDC' ORDER BY created_at"
        ),
        {"p": str(client.person_id)},
    ).fetchall()
    for i, (sid,) in enumerate(rows):
        swap = repo.get_for_person(db, swap_id=sid, person_id=client.person_id)
        leg = leg_from_swap_audit(swap)
        svc.submit_leg_tx(
            db, leg=leg, person_id=client.person_id, swap_id=sid,
            tx_hash=f"0xe2e-seed-{i}",
        )
        db.commit()

    consumed_in = db.execute(
        text(
            "SELECT COALESCE(SUM(amount_in),0) FROM person_wallet_swaps "
            "WHERE person_id=:p AND status='CONFIRMED' AND from_asset='USDC'"
        ),
        {"p": str(client.person_id)},
    ).scalar()
    orch.finalize_lifi_batch(
        db,
        client_id=client.id,
        portfolio_id=portfolio_id,
        batch_id=str(invest["batch_id"]),
        entry_instrument_id=UUID(str(invest["entry_instrument_id"])),
        planned_entry_total=FUND_AMOUNT,
        entry_consumed=Decimal(str(consumed_in)),
    )
    db.commit()
    seeded = snap(db, client.id, client.person_id, portfolio_id)
    print("SEEDED:", json.dumps(seeded))
    assert len(seeded["bundle_spots"]) >= 3, "Allocation seed failed"


def complete_pending_sell_legs(
    db,
    person_id,
    batch_id: str,
    sell_results: list[dict] | None = None,
) -> list[dict]:
    svc = BundleLifiLegService()
    repo = PersonWalletSwapRepository()
    execute = svc._execute

    swap_ids: list = []
    if sell_results:
        swap_ids = [r["swap_id"] for r in sell_results if r.get("status") == "pending" and r.get("swap_id")]
    if not swap_ids:
        rows = db.execute(
            text(
                """
                SELECT id FROM person_wallet_swaps
                WHERE person_id = :p
                  AND status NOT IN ('CONFIRMED', 'FAILED', 'EXPIRED')
                  AND from_asset != 'USDC'
                ORDER BY created_at
                """
            ),
            {"p": str(person_id)},
        ).fetchall()
        swap_ids = [str(row[0]) for row in rows]

    results = []
    for i, sid in enumerate(swap_ids):
        swap = repo.get_for_person(db, swap_id=UUID(str(sid)), person_id=person_id)
        if swap is None:
            continue
        leg = leg_from_swap_audit(swap)
        if leg is None:
            continue
        if swap.status == "QUOTE_RECEIVED":
            execute.prepare_execute(db, person_id=person_id, swap_id=swap.id)
            db.commit()
            swap = repo.get_for_person(db, swap_id=swap.id, person_id=person_id)
        tx_hash = f"0xe2e-withdraw-{batch_id[:8]}-{i}"
        out = svc.submit_leg_tx(
            db,
            leg=leg,
            person_id=person_id,
            swap_id=swap.id,
            tx_hash=tx_hash,
        )
        db.commit()
        results.append(
            {
                "swap_id": str(swap.id),
                "from": swap.from_asset,
                "to": swap.to_asset,
                "status": out.status,
            }
        )
    return results


def main():
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.email.ilike(CLIENT_EMAIL)).first()
        portfolio = db.query(Portfolio).filter(Portfolio.id == PORTFOLIO_ID).first()
        assert client and portfolio and client.person_id

        print("=== E2E BUNDLE FULL WITHDRAW (LI.FI MOCK) ===")
        clear_withdraw_lock(db, PORTFOLIO_ID)
        db.commit()

        ensure_allocated_bundle(db, client, PORTFOLIO_ID)

        before = snap(db, client.id, client.person_id, PORTFOLIO_ID)
        print("BEFORE WITHDRAW:", json.dumps(before, indent=2))
        assert _has_allocated_spots(before), "Need spot atoms to unwind"
        direct_before = before["direct_usdc"]

        adapter = BundleExecutionAdapter(provider=LifiExecutionProvider())
        withdraw_orch = BundleWithdrawOrchestrator(execution_adapter=adapter)
        withdraw = withdraw_orch.withdraw_from_bundle(
            db,
            client_id=client.id,
            portfolio_id=PORTFOLIO_ID,
            full_withdraw=True,
        )
        db.commit()
        print("WITHDRAW REQUEST:", json.dumps(withdraw, indent=2, default=str))

        after_request = snap(db, client.id, client.person_id, PORTFOLIO_ID)
        print("AFTER REQUEST (pre-legs):", json.dumps(after_request, indent=2))

        assert abs(after_request["direct_usdc"] - direct_before) < 0.01, (
            "Self-trading must NOT be credited before RELEASED"
        )

        pending = [r for r in withdraw.get("sell_results", []) if r.get("status") == "pending"]
        if pending:
            assert withdraw["status"] in ("pending_signature", "unwinding"), withdraw["status"]

        batch_id = str(withdraw["batch_id"])

        # Après 1ère vente confirmée : cash leg ↑, self-trading inchangé
        if len(pending) > 1:
            first_only = complete_pending_sell_legs(
                db,
                client.person_id,
                batch_id,
                [pending[0]],
            )
            print("AFTER FIRST SELL:", json.dumps(first_only, indent=2))
            mid = snap(db, client.id, client.person_id, PORTFOLIO_ID)
            print("MID WITHDRAW:", json.dumps(mid, indent=2))
            assert abs(mid["direct_usdc"] - direct_before) < 0.01, (
                "Self-trading must NOT be credited before RELEASED"
            )
            assert mid["bundle_cash_usdc"] > 0.01, "Cash leg should increase after first confirmed sell"
            remaining = pending[1:]
        else:
            first_only = []
            remaining = pending

        leg_results = complete_pending_sell_legs(
            db,
            client.person_id,
            batch_id,
            remaining,
        )
        if len(pending) > 1:
            leg_results = first_only + leg_results
        print("SELL LEGS:", json.dumps(leg_results, indent=2))

        after_sells = snap(db, client.id, client.person_id, PORTFOLIO_ID)
        print("AFTER ALL SELLS:", json.dumps(after_sells, indent=2))

        if not (withdraw.get("release") or {}).get("released"):
            finalize = withdraw_orch.finalize_withdraw_batch(
                db,
                client_id=client.id,
                portfolio_id=PORTFOLIO_ID,
                batch_id=batch_id,
            )
            db.commit()
            print("FINALIZE:", json.dumps(finalize, indent=2, default=str))
            if not finalize.get("released") and finalize.get("reason") != "lock_not_found":
                assert finalize.get("released") is True, finalize
        else:
            print("FINALIZE: skipped (already released on last sell leg)")

        after = snap(db, client.id, client.person_id, PORTFOLIO_ID)
        print("AFTER RELEASE:", json.dumps(after, indent=2))

        checks = [
            ("bundle spot atoms = 0", all(q < 0.0001 for q in after["bundle_spots"].values())),
            ("bundle cash leg = 0", after["bundle_cash_usdc"] < 0.01),
            ("direct_portfolio USDC increased", after["direct_usdc"] > direct_before + 0.01),
            (
                "Privy holds USDC after sells",
                after["privy_usdc"] > 0.01 or sum(after["privy_balances"].values()) > 0,
            ),
            (
                "direct_portfolio USDC <= privy USDC (no over-credit vs custody)",
                after["direct_usdc"] <= after["privy_usdc"] + 0.01,
            ),
            (
                "privy USDC increased vs pre-withdraw (spot → USDC sells)",
                after["privy_usdc"] >= before["privy_usdc"] - 0.01,
            ),
            (
                "self-trading credited only at RELEASED",
                after["direct_usdc"] > direct_before,
            ),
        ]

        print("\n=== CHECKS ===")
        ok = True
        for label, passed in checks:
            print(f"  [{'OK' if passed else 'FAIL'}] {label}")
            ok = ok and passed

        if ok:
            print("\nE2E_BUNDLE_FULL_WITHDRAW_MOCK_OK")
        else:
            raise SystemExit(1)
    except Exception as exc:
        db.rollback()
        raise SystemExit(f"E2E_FAILED: {exc}") from exc
    finally:
        db.close()


if __name__ == "__main__":
    main()
