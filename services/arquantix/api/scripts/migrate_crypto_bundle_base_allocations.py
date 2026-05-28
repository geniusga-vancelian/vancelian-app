#!/usr/bin/env python3
"""
Migrate Base crypto bundle allocations from legacy BTC/ETH instruments to CBBTC/CBETH.

Updates:
  - pe_template_allocations for CRYPTO_BUNDLE_TWO_KINGS / CRYPTO_BUNDLE_CRYPTO_MAJORS
  - pe_target_allocations on all bundle_portfolio rows provisioned from those templates

Mapping (by instrument code):
  BTC-SPOT  → CBBTC-SPOT
  ETH-SPOT  → CBETH-SPOT

Idempotent — safe to re-run.

Usage (from api/):
  python3 scripts/migrate_crypto_bundle_base_allocations.py
  python3 scripts/migrate_crypto_bundle_base_allocations.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from database import SessionLocal
from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.templates.models import PortfolioTemplate, TemplateAllocation

PRODUCT_CODES = (
    "CRYPTO_BUNDLE_TWO_KINGS",
    "CRYPTO_BUNDLE_CRYPTO_MAJORS",
)

INSTRUMENT_REMAP: dict[str, str] = {
    "BTC-SPOT": "CBBTC-SPOT",
    "ETH-SPOT": "CBETH-SPOT",
}


def _load_instrument_map(db) -> dict[str, Instrument]:
    codes = set(INSTRUMENT_REMAP.keys()) | set(INSTRUMENT_REMAP.values())
    rows = db.query(Instrument).filter(Instrument.code.in_(list(codes))).all()
    return {row.code: row for row in rows}


def _migrate_template_allocations(db, template_id, inst_by_code: dict[str, Instrument], dry_run: bool) -> int:
    changed = 0
    for old_code, new_code in INSTRUMENT_REMAP.items():
        old_inst = inst_by_code.get(old_code)
        new_inst = inst_by_code.get(new_code)
        if old_inst is None or new_inst is None:
            continue

        rows = (
            db.query(TemplateAllocation)
            .filter(
                TemplateAllocation.template_id == template_id,
                TemplateAllocation.instrument_id == old_inst.id,
            )
            .all()
        )
        for row in rows:
            existing_new = (
                db.query(TemplateAllocation)
                .filter(
                    TemplateAllocation.template_id == template_id,
                    TemplateAllocation.instrument_id == new_inst.id,
                )
                .first()
            )
            if existing_new is not None and existing_new.id != row.id:
                print(
                    f"    ~ template: merge {old_code} → {new_code} "
                    f"(drop duplicate {old_code}, keep weight on {new_code})"
                )
                if not dry_run:
                    existing_new.target_weight = row.target_weight
                    db.delete(row)
                changed += 1
                continue

            print(f"    ~ template: {old_code} → {new_code} (weight={row.target_weight})")
            if not dry_run:
                row.instrument_id = new_inst.id
            changed += 1

    return changed


def _migrate_portfolio_allocations(db, portfolio_id, inst_by_code: dict[str, Instrument], dry_run: bool) -> int:
    changed = 0
    for old_code, new_code in INSTRUMENT_REMAP.items():
        old_inst = inst_by_code.get(old_code)
        new_inst = inst_by_code.get(new_code)
        if old_inst is None or new_inst is None:
            continue

        rows = (
            db.query(TargetAllocation)
            .filter(
                TargetAllocation.portfolio_id == portfolio_id,
                TargetAllocation.instrument_id == old_inst.id,
            )
            .all()
        )
        for row in rows:
            existing_new = (
                db.query(TargetAllocation)
                .filter(
                    TargetAllocation.portfolio_id == portfolio_id,
                    TargetAllocation.instrument_id == new_inst.id,
                )
                .first()
            )
            if existing_new is not None and existing_new.id != row.id:
                print(
                    f"      ~ portfolio {str(portfolio_id)[:8]}…: merge {old_code} → {new_code}"
                )
                if not dry_run:
                    existing_new.target_weight = row.target_weight
                    db.delete(row)
                changed += 1
                continue

            print(f"      ~ portfolio {str(portfolio_id)[:8]}…: {old_code} → {new_code}")
            if not dry_run:
                row.instrument_id = new_inst.id
            changed += 1

    return changed


def migrate(*, dry_run: bool) -> None:
    db = SessionLocal()
    try:
        inst_by_code = _load_instrument_map(db)
        missing = [c for c in set(INSTRUMENT_REMAP.values()) if c not in inst_by_code]
        if missing:
            print(f"  ✗ FATAL: missing target instruments: {missing}")
            print("    Run: python3 scripts/sync_base_allowed_instruments.py")
            print("         python3 scripts/seed_pe_crypto_assets.py")
            sys.exit(1)

        total_template = 0
        total_portfolio = 0

        for product_code in PRODUCT_CODES:
            product = (
                db.query(ProductDefinition)
                .filter(ProductDefinition.product_code == product_code)
                .first()
            )
            if product is None:
                print(f"  = skip (no product): {product_code}")
                continue

            template = (
                db.query(PortfolioTemplate)
                .filter(
                    PortfolioTemplate.product_id == product.id,
                    PortfolioTemplate.provisioned_portfolio_type == "bundle_portfolio",
                )
                .first()
            )
            if template is None:
                print(f"  = skip (no template): {product_code}")
                continue

            print(f"  ── {product_code} (template {template.template_code}) ──")
            total_template += _migrate_template_allocations(db, template.id, inst_by_code, dry_run)

            portfolios = (
                db.query(Portfolio)
                .filter(
                    Portfolio.origin_product_id == product.id,
                    Portfolio.portfolio_type == "bundle_portfolio",
                )
                .all()
            )
            for portfolio in portfolios:
                total_portfolio += _migrate_portfolio_allocations(
                    db, portfolio.id, inst_by_code, dry_run,
                )

        if dry_run:
            db.rollback()
            print()
            print(f"  DRY RUN — would update {total_template} template row(s), "
                  f"{total_portfolio} portfolio row(s)")
        else:
            db.commit()
            print()
            print(f"  ✓ Updated {total_template} template row(s), "
                  f"{total_portfolio} portfolio row(s)")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate bundle allocations BTC/ETH → CBBTC/CBETH")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without committing")
    args = parser.parse_args()
    print("Migrating Base crypto bundle allocations (BTC/ETH → CBBTC/CBETH)...")
    if args.dry_run:
        print("  (dry run — no commit)")
    print()
    migrate(dry_run=args.dry_run)
    print()
    print("Done.")


if __name__ == "__main__":
    main()
