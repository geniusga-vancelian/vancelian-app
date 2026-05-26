#!/usr/bin/env python3
"""Pilote local LI.FI bundle (mock) — invest + legs + finalize + invariant G.

Usage (dans le conteneur API, avec la DB Compose montée) :

  docker exec -e BUNDLE_EXECUTION_PROVIDER=lifi_base \\
    -e LIFI_SWAPS_ENABLED=1 -e LIFI_SWAPS_MOCK=1 -e BUNDLE_LIFI_SYNC_MOCK=1 \\
    arquantixrecovery-arquantix-api-1 \\
    python3 scripts/pilot_bundle_lifi_invest_mock.py [--amount 50] [--asset USDC]

Ne modifie pas la config Compose ; variables passées uniquement à l'exécution.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from decimal import Decimal

# Forcer le pilote LI.FI mock si non défini
os.environ.setdefault("BUNDLE_EXECUTION_PROVIDER", "lifi_base")
os.environ.setdefault("LIFI_SWAPS_ENABLED", "1")
os.environ.setdefault("LIFI_SWAPS_MOCK", "1")
os.environ.setdefault("BUNDLE_LIFI_SYNC_MOCK", "1")

from database import SessionLocal  # noqa: E402
from services.portfolio_engine.bundle_execution import BundleExecutionAdapter  # noqa: E402
from services.portfolio_engine.bundle_execution.config import get_bundle_execution_provider_name  # noqa: E402
from services.portfolio_engine.bundle_execution.lifi_provider import LifiExecutionProvider  # noqa: E402
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator  # noqa: E402
from services.portfolio_engine.clients.models import Client  # noqa: E402
from services.portfolio_engine.portfolios.models import Portfolio  # noqa: E402
from services.portfolio_engine.products.models import ProductDefinition  # noqa: E402
from services.portfolio_engine.positions.models import PositionAtom  # noqa: E402


def _ok(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")
    print(f"OK: {msg}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amount", type=float, default=50.0)
    parser.add_argument("--asset", default="USDC")
    parser.add_argument("--product-code", default="TOP_5")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        product = (
            db.query(ProductDefinition)
            .filter(
                ProductDefinition.product_code == args.product_code,
                ProductDefinition.product_type == "crypto_bundle",
            )
            .first()
        )
        _ok(product is not None, f"product {args.product_code} found")

        portfolio = (
            db.query(Portfolio)
            .filter(
                Portfolio.origin_product_id == product.id,
                Portfolio.portfolio_type == "bundle_portfolio",
                Portfolio.status == "active",
            )
            .first()
        )
        if portfolio is None:
            client = db.query(Client).filter(Client.status == "active").first()
            _ok(client is not None, "at least one active PE client")
            raise SystemExit(
                "No bundle portfolio for product — open Portal Markets once to auto-provision."
            )

        _ok(str(portfolio.id), f"portfolio_id={portfolio.id}")

        atoms_before = (
            db.query(PositionAtom)
            .filter(PositionAtom.portfolio_id == portfolio.id)
            .count()
        )

        provider_name = get_bundle_execution_provider_name()
        print(f"PROVIDER_ENV={provider_name}")
        adapter = BundleExecutionAdapter(
            provider=LifiExecutionProvider()
            if provider_name in ("lifi_base", "lifi")
            else None
        )
        orch = BundleOrchestrator(execution_adapter=adapter)
        _ok(orch._execution.provider_name == "lifi_base", "orchestrator uses lifi_base adapter")
        invest = orch.invest_into_bundle(
            db,
            client_id=portfolio.client_id,
            portfolio_id=portfolio.id,
            funding_asset=args.asset.upper(),
            funding_amount=Decimal(str(args.amount)),
        )
        db.commit()

        print("INVEST:", json.dumps(invest, indent=2, default=str))

        _ok(invest.get("portfolio_id") == str(portfolio.id), "portfolio_id in response")
        _ok(bool(invest.get("batch_id")), "batch_id present")
        _ok(invest.get("execution_provider") == "lifi_base", "execution_provider=lifi_base")

        pending = [
            leg
            for leg in invest.get("allocation_details") or []
            if leg.get("status") == "pending"
        ]
        entry_iid = invest.get("entry_instrument_id")

        if pending:
            _ok(invest.get("status") in ("pending_signature", "partial_pending"), "pending_signature status")
            for leg in pending:
                _ok(bool(leg.get("swap_id")), f"swap_id for leg {leg.get('asset')}")
            _ok(bool(entry_iid), "entry_instrument_id present (LI.FI path)")

            if os.environ.get("BUNDLE_LIFI_SYNC_MOCK") == "1":
                print("NOTE: BUNDLE_LIFI_SYNC_MOCK=1 may auto-complete legs during invest.")
        else:
            _ok(invest.get("status") == "completed", "completed without pending (sync mock)")

        if pending and entry_iid and invest.get("status") != "completed":
            consumed = Decimal(str(invest.get("total_entry_asset_consumed") or 0))
            planned = Decimal(str(invest.get("total_entry_asset_received") or args.amount))
            from services.portfolio_engine.instruments.models import Instrument

            entry_inst = db.query(Instrument).filter(Instrument.id == uuid.UUID(str(entry_iid))).first()
            _ok(entry_inst is not None, "entry instrument resolvable")

            finalize = orch.finalize_lifi_batch(
                db,
                client_id=portfolio.client_id,
                portfolio_id=portfolio.id,
                batch_id=str(invest["batch_id"]),
                entry_instrument_id=uuid.UUID(str(entry_iid)),
                planned_entry_total=planned,
                entry_consumed=consumed,
            )
            db.commit()
            print("FINALIZE:", json.dumps(finalize, indent=2, default=str))
            _ok("invariant_g" in finalize, "invariant_g in finalize response")
            ig = finalize.get("invariant_g") or {}
            _ok(ig.get("dry_run") is True or ig.get("mode") == "dry_run" or "violations" in ig, "invariant_g dry-run shape")
        elif invest.get("invariant_g"):
            ig = invest["invariant_g"]
            print("INVARIANT_G (invest):", json.dumps(ig, indent=2, default=str))

        atoms_after = (
            db.query(PositionAtom)
            .filter(PositionAtom.portfolio_id == portfolio.id)
            .count()
        )
        print(f"pe_position_atoms count: before={atoms_before} after={atoms_after}")

        print("\nPILOT_MOCK_OK")
    except Exception as exc:
        db.rollback()
        raise SystemExit(f"PILOT_FAILED: {exc}") from exc
    finally:
        db.close()


if __name__ == "__main__":
    main()
