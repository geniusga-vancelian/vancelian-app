#!/usr/bin/env python3
"""
Script pour s'assurer que les instruments CORE_V1 sont présents dans la base
avec provider="yahoo" (et non "alphavantage").

Usage: python3 api/scripts/ensure_yahoo_instruments.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import SessionLocal, MarketDataInstrument
from services.market_data.routes import CORE_V1_INSTRUMENTS

def ensure_yahoo_instruments():
    """S'assure que tous les instruments CORE_V1 existent avec provider='yahoo'"""
    db = SessionLocal()
    try:
        created = []
        updated = []
        
        for inst_def in CORE_V1_INSTRUMENTS:
            existing = db.query(MarketDataInstrument).filter(
                MarketDataInstrument.symbol == inst_def["symbol"]
            ).first()
            
            if not existing:
                # Créer l'instrument avec provider="yahoo"
                new_inst = MarketDataInstrument(
                    symbol=inst_def["symbol"],
                    name=inst_def["name"],
                    asset_class=inst_def["asset_class"],
                    weekend_tradable=inst_def["weekend_tradable"],
                    provider="yahoo",  # Yahoo Finance uniquement
                    provider_symbol=inst_def["symbol"],
                    is_active="true",
                )
                db.add(new_inst)
                created.append(new_inst)
                print(f"  → Créé: {inst_def['symbol']} (provider: yahoo)")
            elif existing.provider != "yahoo":
                # Mettre à jour l'instrument existant pour utiliser Yahoo Finance
                existing.provider = "yahoo"
                existing.is_active = "true"
                updated.append(existing)
                print(f"  → Mis à jour: {inst_def['symbol']} (provider: {existing.provider} -> yahoo)")
            else:
                # Déjà présent avec provider="yahoo"
                if existing.is_active != "true":
                    existing.is_active = "true"
                    updated.append(existing)
                    print(f"  → Activé: {inst_def['symbol']} (était inactif)")
        
        if created or updated:
            db.commit()
            for inst in created:
                db.refresh(inst)
            for inst in updated:
                db.refresh(inst)
            
            if created:
                print(f"  ✅ {len(created)} instrument(s) créé(s)")
            if updated:
                print(f"  ✅ {len(updated)} instrument(s) mis à jour")
        else:
            print("  ✅ Tous les instruments CORE_V1 sont déjà présents avec provider='yahoo'")
        
        # Vérifier le nombre total d'instruments Yahoo Finance
        yahoo_count = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.provider == "yahoo",
            MarketDataInstrument.is_active == "true"
        ).count()
        
        print(f"  ✅ Total: {yahoo_count} instrument(s) Yahoo Finance actif(s)")
        
        return created, updated
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de l'initialisation: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║     INITIALISATION INSTRUMENTS YAHOO FINANCE                              ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
    print("")
    ensure_yahoo_instruments()
    print("")
    print("✅ Initialisation terminée avec succès")
