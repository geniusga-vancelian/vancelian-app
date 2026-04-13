#!/usr/bin/env python3
"""
Bootstrap: Crypto Bundle Top 5 — produit PE + template + allocations.

Allocation cible:
  BTC 50%, ETH 20%, SOL 10%, XRP 10%, BNB 10%  (somme = 100%)

Entrée investissement:
  USDC comme asset de dépôt / devise d’entrée (metadata entry_asset_*).
  L’USDC n’est pas une ligne d’allocation du bundle.

Prérequis:
  pe_instruments BTC-SPOT, ETH-SPOT, SOL-SPOT, XRP-SPOT, BNB-SPOT.
  Exécuter seed_pe_crypto_assets.py si besoin.

Idempotent: ré-exécution sans doublon d’allocations (clé template + instrument).
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

PRODUCT_CODE = "CRYPTO_BUNDLE_TOP5"
TEMPLATE_CODE = "CRYPTO_BUNDLE_TOP5_DEFAULT"

SHORT_DESCRIPTION = (
    "Produit diversifié exposé aux cinq principaux crypto-actifs, avec une pondération "
    "dominante sur Bitcoin et Ethereum pour offrir un équilibre entre solidité de marché "
    "et potentiel de croissance."
)

DESCRIPTION = (
    SHORT_DESCRIPTION
    + " "
    "Les performances passées ne préjugent pas des performances futures. "
    "Investissement en crypto-actifs, à risque élevé de perte en capital."
)

PRODUCT_CONFIG = {
    "product_code": PRODUCT_CODE,
    "name": "Top 5 Crypto Bundle",
    "description": DESCRIPTION,
    "product_type": "crypto_bundle",
    "risk_label": "high",
    "base_currency": "USD",
    "is_public": True,
    "status": "active",
    "metadata_": {
        "short_description": SHORT_DESCRIPTION,
        "available_rebalance_frequencies": ["weekly", "monthly", "quarterly"],
        "entry_asset_default": "USDC",
        "entry_assets_allowed": ["USDC"],
        "subscription_note": (
            "Souscription en USDC ; allocation exécutée vers les actifs cibles selon les poids indiqués."
        ),
        "product_category": "crypto_bundle",
    },
}

ALLOCATIONS = [
    {"instrument_code": "BTC-SPOT", "target_weight": Decimal("0.500000")},
    {"instrument_code": "ETH-SPOT", "target_weight": Decimal("0.200000")},
    {"instrument_code": "SOL-SPOT", "target_weight": Decimal("0.100000")},
    {"instrument_code": "XRP-SPOT", "target_weight": Decimal("0.100000")},
    {"instrument_code": "BNB-SPOT", "target_weight": Decimal("0.100000")},
]


def _verify_weights() -> None:
    s = sum(a["target_weight"] for a in ALLOCATIONS)
    if abs(s - Decimal("1")) > Decimal("0.000001"):
        raise SystemExit(f"Internal error: weights sum to {s}, expected 1")


def bootstrap() -> None:
    _verify_weights()
    db = SessionLocal()
    try:
        codes = [a["instrument_code"] for a in ALLOCATIONS]
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
            print("    Run: python3 scripts/seed_pe_crypto_assets.py")
            sys.exit(1)

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
            # Mettre à jour métadonnées et textes si déjà présent (idempotence enrichie)
            product.name = PRODUCT_CONFIG["name"]
            product.description = PRODUCT_CONFIG["description"]
            product.is_public = PRODUCT_CONFIG["is_public"]
            product.status = PRODUCT_CONFIG["status"]
            product.risk_label = PRODUCT_CONFIG["risk_label"]
            product.base_currency = PRODUCT_CONFIG["base_currency"]
            product.metadata_ = {**(product.metadata_ or {}), **PRODUCT_CONFIG["metadata_"]}
            db.flush()
            print("  ~ ProductDefinition metadata / description refreshed")

        template = db.query(PortfolioTemplate).filter(
            PortfolioTemplate.template_code == TEMPLATE_CODE
        ).first()

        if template is None:
            template = PortfolioTemplate(
                product_id=product.id,
                template_code=TEMPLATE_CODE,
                provisioned_portfolio_type="bundle_portfolio",
                name="Top 5 Crypto Bundle — Default Template",
                description="50% BTC / 20% ETH / 10% SOL / 10% XRP / 10% BNB.",
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
                if existing.target_weight != alloc_cfg["target_weight"]:
                    existing.target_weight = alloc_cfg["target_weight"]
                    db.flush()
                    print(f"  ~ TemplateAllocation UPDATED: {code} = {alloc_cfg['target_weight']}")
                else:
                    print(f"  = TemplateAllocation OK: {code} = {existing.target_weight}")

        db.commit()
        print()
        print("  ── Bootstrap complete ──")
        print(f"  Product:    {PRODUCT_CODE} (id={product.id})")
        print(f"  Template:   {TEMPLATE_CODE} (id={template.id})")
        print("  Entry:      USDC (entry_asset_default / entry_assets_allowed in metadata)")
        print("  Allocations: BTC 50% | ETH 20% | SOL 10% | XRP 10% | BNB 10%")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Bootstrapping Top 5 Crypto Bundle (CRYPTO_BUNDLE_TOP5)...")
    print()
    bootstrap()
    print()
    print("Done.")
