#!/usr/bin/env python3
"""
Bootstrap: Crypto Bundle Top 2 product + template + allocations.

Creates:
  1. ProductDefinition  CRYPTO_BUNDLE_TOP2  (crypto_bundle, active, public)
  2. PortfolioTemplate   CRYPTO_BUNDLE_TOP2_DEFAULT
  3. TemplateAllocation  BTC-SPOT  70%
  4. TemplateAllocation  ETH-SPOT  30%

Prerequisites:
  - pe_instruments with codes BTC-SPOT and ETH-SPOT must exist.
    Run seed_pe_crypto_assets.py first if needed.

Idempotent: safe to run multiple times.
"""
import sys
from decimal import Decimal
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from database import SessionLocal
from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.templates.models import PortfolioTemplate, TemplateAllocation
from services.portfolio_engine.instruments.models import Instrument

PRODUCT_CODE = "CRYPTO_BUNDLE_TOP2"
TEMPLATE_CODE = "CRYPTO_BUNDLE_TOP2_DEFAULT"

PRODUCT_CONFIG = {
    "product_code": PRODUCT_CODE,
    "name": "Crypto Bundle Top 2",
    "description": "A simple crypto allocation strategy composed of 70% BTC and 30% ETH.",
    "product_type": "crypto_bundle",
    "risk_label": "high",
    "base_currency": "USD",
    "is_public": True,
    "status": "active",
    "metadata_": {
        "short_description": "A simple crypto allocation strategy composed of 70% BTC and 30% ETH.",
        "available_rebalance_frequencies": ["weekly", "monthly", "quarterly"],
    },
}

ALLOCATIONS = [
    {"instrument_code": "BTC-SPOT", "target_weight": Decimal("0.700000")},
    {"instrument_code": "ETH-SPOT", "target_weight": Decimal("0.300000")},
]


def bootstrap() -> None:
    db = SessionLocal()
    try:
        btc_inst = db.query(Instrument).filter(Instrument.code == "BTC-SPOT").first()
        eth_inst = db.query(Instrument).filter(Instrument.code == "ETH-SPOT").first()

        missing = []
        if btc_inst is None:
            missing.append("BTC-SPOT")
        if eth_inst is None:
            missing.append("ETH-SPOT")
        if missing:
            print(f"  ✗ FATAL: missing pe_instruments: {missing}")
            print("    Run seed_pe_crypto_assets.py first.")
            sys.exit(1)

        inst_map = {"BTC-SPOT": btc_inst, "ETH-SPOT": eth_inst}

        product = db.query(ProductDefinition).filter(
            ProductDefinition.product_code == PRODUCT_CODE
        ).first()

        if product is None:
            product = ProductDefinition(**PRODUCT_CONFIG)
            db.add(product)
            db.flush()
            print(f"  + ProductDefinition CREATED: {PRODUCT_CODE} (id={product.id})")
        else:
            print(f"  = ProductDefinition EXISTS: {PRODUCT_CODE} (id={product.id})")

        template = db.query(PortfolioTemplate).filter(
            PortfolioTemplate.template_code == TEMPLATE_CODE
        ).first()

        if template is None:
            template = PortfolioTemplate(
                product_id=product.id,
                template_code=TEMPLATE_CODE,
                provisioned_portfolio_type="bundle_portfolio",
                name="Crypto Bundle Top 2 — Default Template",
                description="70% BTC / 30% ETH allocation template.",
                base_currency="USD",
                risk_profile="high",
                strategy_definition_id=None,
                metadata_={},
            )
            db.add(template)
            db.flush()
            print(f"  + PortfolioTemplate CREATED: {TEMPLATE_CODE} (id={template.id})")
        else:
            print(f"  = PortfolioTemplate EXISTS: {TEMPLATE_CODE} (id={template.id})")

        for alloc_cfg in ALLOCATIONS:
            code = alloc_cfg["instrument_code"]
            instrument = inst_map[code]

            existing = db.query(TemplateAllocation).filter(
                TemplateAllocation.template_id == template.id,
                TemplateAllocation.instrument_id == instrument.id,
            ).first()

            if existing is None:
                ta = TemplateAllocation(
                    template_id=template.id,
                    instrument_id=instrument.id,
                    target_weight=alloc_cfg["target_weight"],
                    allocation_priority=100,
                )
                db.add(ta)
                db.flush()
                print(f"  + TemplateAllocation CREATED: {code} = {alloc_cfg['target_weight']}")
            else:
                print(f"  = TemplateAllocation EXISTS: {code} = {existing.target_weight}")

        db.commit()
        print()
        print("  ── Bootstrap complete ──")
        print(f"  Product:    {PRODUCT_CODE} (id={product.id})")
        print(f"  Template:   {TEMPLATE_CODE} (id={template.id})")
        print(f"  Allocations: BTC-SPOT 70% / ETH-SPOT 30%")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Bootstrapping Crypto Bundle Top 2...")
    print()
    bootstrap()
    print()
    print("Done.")
