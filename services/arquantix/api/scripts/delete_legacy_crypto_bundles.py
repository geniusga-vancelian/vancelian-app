#!/usr/bin/env python3
"""
Remove legacy crypto bundles (TOP 5, TOP 2, CRYPTO_BUNDLE_TOP5, …) from Portfolio Engine.

Keeps only the current Base portfolio bundles (Two Crypto Kings, Crypto Majors).
Also run the web CMS cleanup:

  cd ../web && npx tsx scripts/delete-legacy-crypto-bundle-configs.ts

Idempotent. Skips products with active subscriptions (prints error).
"""
from __future__ import annotations

import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from database import SessionLocal
from services.portfolio_engine.bundles.service import (
    BundleEngineService,
    BundleHasSubscriptionsError,
    BundleNotFoundError,
)
from services.portfolio_engine.products.models import ProductDefinition

LEGACY_PRODUCT_CODES = (
    "TOP_5",
    "TOP_2",
    "CRYPTO_BUNDLE_TOP5",
    "CRYPTO_BUNDLE_TOP_5",
    "CRYPTO_BUNDLE_TOP2",
    "CRYPTO_BUNDLE_TOP_2",
)


def delete_legacy_bundles() -> None:
    db = SessionLocal()
    svc = BundleEngineService()
    try:
        for code in LEGACY_PRODUCT_CODES:
            product = (
                db.query(ProductDefinition)
                .filter(
                    ProductDefinition.product_code == code,
                    ProductDefinition.product_type == "crypto_bundle",
                )
                .first()
            )
            if product is None:
                print(f"  = Not found (skip): {code}")
                continue
            try:
                result = svc.delete_bundle(
                    db,
                    product.id,
                    actor_type="admin",
                    actor_id="delete_legacy_crypto_bundles",
                )
                print(f"  ✓ Deleted PE bundle: {code} ({result['product_id']})")
            except BundleHasSubscriptionsError as exc:
                print(f"  ✗ Cannot delete {code}: {exc}")
                db.rollback()
                continue
        db.commit()
        remaining = (
            db.query(ProductDefinition)
            .filter(ProductDefinition.product_type == "crypto_bundle")
            .order_by(ProductDefinition.product_code)
            .all()
        )
        print()
        print("  Remaining crypto_bundle products:")
        for p in remaining:
            print(f"    - {p.product_code} ({p.name})")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Deleting legacy crypto bundles from Portfolio Engine...")
    print()
    delete_legacy_bundles()
    print()
    print("Done.")
