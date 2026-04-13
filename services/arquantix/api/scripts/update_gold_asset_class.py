#!/usr/bin/env python3
"""
Script pour mettre à jour l'asset_class de GOLD de "METAL" à "COMMODITIES"
"""
import sys
from pathlib import Path

# Add parent directory to path to import database models
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

from database import SessionLocal, MarketDataInstrument
from sqlalchemy import or_

def update_gold_asset_class():
    """Mettre à jour GOLD de METAL à COMMODITIES"""
    db = SessionLocal()
    try:
        # Rechercher GOLD (peut être en majuscules, minuscules, ou mixte)
        instruments = db.query(MarketDataInstrument).filter(
            or_(
                MarketDataInstrument.symbol.ilike('%GOLD%'),
                MarketDataInstrument.provider_symbol.ilike('%GOLD%')
            )
        ).all()
        
        if not instruments:
            print("❌ Aucun instrument GOLD trouvé dans la base de données")
            return
        
        print(f"📊 Trouvé {len(instruments)} instrument(s) GOLD:")
        updated_count = 0
        
        for inst in instruments:
            print(f"\n  - ID: {inst.id}")
            print(f"    Symbol: {inst.symbol}")
            print(f"    Provider Symbol: {inst.provider_symbol}")
            print(f"    Asset Class actuel: {inst.asset_class}")
            
            # Mettre à jour vers COMMODITIES (peu importe la valeur actuelle)
            if inst.asset_class and inst.asset_class.upper() == "COMMODITIES":
                print(f"    ℹ️  Déjà en COMMODITIES")
            else:
                old_class = inst.asset_class
                inst.asset_class = "COMMODITIES"
                updated_count += 1
                print(f"    ✅ Mis à jour: '{old_class}' → 'COMMODITIES'")
        
        if updated_count > 0:
            db.commit()
            print(f"\n✅ {updated_count} instrument(s) mis à jour avec succès")
        else:
            print("\nℹ️  Aucune mise à jour nécessaire")
            
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la mise à jour: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🔄 Mise à jour de l'asset_class de GOLD...")
    update_gold_asset_class()
    print("✅ Terminé")

