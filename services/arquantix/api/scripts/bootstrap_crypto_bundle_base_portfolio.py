#!/usr/bin/env python3
"""
Bootstrap: two Base crypto bundles (Portfolio Engine).

Legacy TOP 2 / TOP 5 bundles must be removed separately:
  python3 scripts/delete_legacy_crypto_bundles.py
  cd ../web && npx tsx scripts/delete-legacy-crypto-bundle-configs.ts

1. CRYPTO_BUNDLE_TWO_KINGS — Bitcoin 70% / Ethereum 30% (cbBTC + cbETH on Base)
2. CRYPTO_BUNDLE_CRYPTO_MAJORS — Bitcoin 50% / Ethereum 30% / LINK, AAVE, UNI ~6.7% each

Prerequisites:
  python3 scripts/sync_base_allowed_instruments.py
  python3 scripts/seed_pe_crypto_assets.py

CMS UI config: web/scripts/seed-crypto-base-bundles-portfolio-config.ts

Idempotent.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from database import SessionLocal
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.templates.models import PortfolioTemplate, TemplateAllocation

BUNDLES: tuple[dict, ...] = (
    {
        "product_code": "CRYPTO_BUNDLE_TWO_KINGS",
        "template_code": "CRYPTO_BUNDLE_TWO_KINGS_DEFAULT",
        "name": "Two Crypto Kings",
        "short_description": (
            "A concentrated two-asset bundle built around the two largest crypto networks: "
            "Bitcoin and Ethereum. Ideal for investors who want a simple, transparent core allocation."
        ),
        "description": (
            "Two Crypto Kings is a focused crypto bundle for the Base network. "
            "Bitcoin exposure is implemented via Coinbase Wrapped BTC (cbBTC), representing 70% of the target "
            "allocation, while Ethereum exposure uses Coinbase Wrapped ETH (cbETH) for the remaining 30%. "
            "Subscribe in USDC; the strategy rebalances toward these weights over time. "
            "Past performance is not indicative of future results. Crypto assets carry a high risk of capital loss."
        ),
        "template_description": "70% Bitcoin (cbBTC) / 30% Ethereum (cbETH).",
        "sort_hint": 10,
        "allocations": [
            {"instrument_code": "CBBTC-SPOT", "target_weight": Decimal("0.700000")},
            {"instrument_code": "CBETH-SPOT", "target_weight": Decimal("0.300000")},
        ],
    },
    {
        "product_code": "CRYPTO_BUNDLE_CRYPTO_MAJORS",
        "template_code": "CRYPTO_BUNDLE_CRYPTO_MAJORS_DEFAULT",
        "name": "Crypto Majors",
        "short_description": (
            "A diversified bundle across Bitcoin, Ethereum, and three established DeFi leaders: "
            "Chainlink, Aave, and Uniswap."
        ),
        "description": (
            "Crypto Majors combines the two largest crypto assets with three infrastructure and DeFi blue chips "
            "available on Base. The target allocation is 50% Bitcoin (cbBTC), 30% Ethereum (cbETH), and 20% split equally "
            "across Chainlink, Aave, and Uniswap (~6.7% each). "
            "Subscribe in USDC to gain diversified exposure without managing individual positions. "
            "Past performance is not indicative of future results. Crypto assets carry a high risk of capital loss."
        ),
        "template_description": "50% Bitcoin (cbBTC) / 30% Ethereum (cbETH) / ~6.7% each on Chainlink, Aave, Uniswap.",
        "sort_hint": 20,
        "allocations": [
            {"instrument_code": "CBBTC-SPOT", "target_weight": Decimal("0.500000")},
            {"instrument_code": "CBETH-SPOT", "target_weight": Decimal("0.300000")},
            {"instrument_code": "LINK-SPOT", "target_weight": Decimal("0.066667")},
            {"instrument_code": "AAVE-SPOT", "target_weight": Decimal("0.066667")},
            {"instrument_code": "UNI-SPOT", "target_weight": Decimal("0.066666")},
        ],
    },
)


def _common_metadata(short_description: str) -> dict:
    return {
        "short_description": short_description,
        "available_rebalance_frequencies": ["weekly", "monthly", "quarterly"],
        "entry_asset_default": "USDC",
        "entry_assets_allowed": ["USDC"],
        "subscription_note": (
            "Subscribe in USDC on Base; allocations are executed toward the target weights via on-chain swaps."
        ),
        "product_category": "crypto_bundle",
    }


def _verify_weights(allocations: list[dict]) -> None:
    total = sum(a["target_weight"] for a in allocations)
    if abs(total - Decimal("1")) > Decimal("0.00001"):
        raise SystemExit(f"Internal error: weights sum to {total}, expected 1")


def _load_instruments(db, codes: list[str]) -> dict[str, Instrument]:
    inst_map: dict[str, Instrument] = {}
    missing: list[str] = []
    for code in codes:
        inst = db.query(Instrument).filter(Instrument.code == code).first()
        if inst is None:
            missing.append(code)
        else:
            inst_map[code] = inst
    if missing:
        print(f"  ✗ FATAL: missing pe_instruments: {missing}")
        print("    Run: python3 scripts/sync_base_allowed_instruments.py")
        print("         python3 scripts/seed_pe_crypto_assets.py")
        sys.exit(1)
    return inst_map


def _upsert_bundle(db, spec: dict) -> None:
    _verify_weights(spec["allocations"])
    codes = [a["instrument_code"] for a in spec["allocations"]]
    inst_map = _load_instruments(db, codes)
    expected_ids = set()

    product_code = spec["product_code"]
    template_code = spec["template_code"]
    metadata = _common_metadata(spec["short_description"])

    product = db.query(ProductDefinition).filter(
        ProductDefinition.product_code == product_code
    ).first()

    product_fields = {
        "product_code": product_code,
        "name": spec["name"],
        "description": spec["description"],
        "product_type": "crypto_bundle",
        "risk_label": "high",
        "base_currency": "USD",
        "is_public": True,
        "status": "active",
        "metadata_": metadata,
    }

    if product is None:
        product = ProductDefinition(**product_fields)
        db.add(product)
        db.flush()
        print(f"  + ProductDefinition CREATED: {product_code} (id={product.id})")
    else:
        for key, value in product_fields.items():
            if key == "metadata_":
                product.metadata_ = {**(product.metadata_ or {}), **value}
            else:
                setattr(product, key, value)
        db.flush()
        print(f"  ~ ProductDefinition UPDATED: {product_code} (id={product.id})")

    template = db.query(PortfolioTemplate).filter(
        PortfolioTemplate.template_code == template_code
    ).first()

    if template is None:
        template = PortfolioTemplate(
            product_id=product.id,
            template_code=template_code,
            provisioned_portfolio_type="bundle_portfolio",
            name=f"{spec['name']} — Default Template",
            description=spec["template_description"],
            base_currency="USD",
            risk_profile="high",
            strategy_definition_id=None,
            metadata_={},
        )
        db.add(template)
        db.flush()
        print(f"  + PortfolioTemplate CREATED: {template_code} (id={template.id})")
    else:
        template.description = spec["template_description"]
        db.flush()
        print(f"  = PortfolioTemplate EXISTS: {template_code} (id={template.id})")

    for alloc_cfg in spec["allocations"]:
        code = alloc_cfg["instrument_code"]
        instrument = inst_map[code]
        expected_ids.add(instrument.id)
        existing = db.query(TemplateAllocation).filter(
            TemplateAllocation.template_id == template.id,
            TemplateAllocation.instrument_id == instrument.id,
        ).first()

        if existing is None:
            db.add(
                TemplateAllocation(
                    template_id=template.id,
                    instrument_id=instrument.id,
                    target_weight=alloc_cfg["target_weight"],
                    allocation_priority=100,
                )
            )
            db.flush()
            print(f"  + TemplateAllocation CREATED: {code} = {alloc_cfg['target_weight']}")
        elif existing.target_weight != alloc_cfg["target_weight"]:
            existing.target_weight = alloc_cfg["target_weight"]
            db.flush()
            print(f"  ~ TemplateAllocation UPDATED: {code} = {alloc_cfg['target_weight']}")
        else:
            print(f"  = TemplateAllocation OK: {code} = {existing.target_weight}")

    stale = (
        db.query(TemplateAllocation)
        .filter(
            TemplateAllocation.template_id == template.id,
            ~TemplateAllocation.instrument_id.in_(expected_ids),
        )
        .all()
    )
    for row in stale:
        stale_inst = db.query(Instrument).filter(Instrument.id == row.instrument_id).first()
        stale_code = stale_inst.code if stale_inst else str(row.instrument_id)
        db.delete(row)
        db.flush()
        print(f"  - TemplateAllocation REMOVED (stale): {stale_code}")


def bootstrap() -> None:
    db = SessionLocal()
    try:
        print("  ── Two Crypto Kings ──")
        _upsert_bundle(db, BUNDLES[0])
        print()
        print("  ── Crypto Majors ──")
        _upsert_bundle(db, BUNDLES[1])
        db.commit()
        print()
        print("  ── Bootstrap complete ──")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Bootstrapping Base crypto bundles (Two Crypto Kings + Crypto Majors)...")
    print()
    bootstrap()
    print()
    print("Done. Next: cd ../web && npx tsx scripts/seed-crypto-base-bundles-portfolio-config.ts")
