#!/usr/bin/env python3
"""
Script pour reclasser les indices boursiers de "etf" vers "index"
"""
import sys
from pathlib import Path

# Add parent directory to path to import database models
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

from database import SessionLocal, MarketDataInstrument

# Liste des symboles d'instruments qui sont des indices (pas des ETF)
INDEX_SYMBOLS = [
    'S&P 500',
    'DOW JONES',
    'NASDAQ 100',
    'EURONEXT 100',
    'DAX',
    'CAC 40',
    'US DOLLAR INDEX',
    'MSCI'
]

def fix_index_asset_class():
    """Reclasser les indices de 'etf' vers 'index'"""
    db = SessionLocal()
    try:
        updated_count = 0
        
        for symbol in INDEX_SYMBOLS:
            instrument = db.query(MarketDataInstrument).filter(
                MarketDataInstrument.symbol == symbol
            ).first()
            
            if instrument:
                print(f'\n📊 {symbol}:')
                print(f'  Asset Class actuel: {instrument.asset_class}')
                
                if instrument.asset_class.lower() == 'etf':
                    instrument.asset_class = 'index'
                    updated_count += 1
                    print(f'  ✅ Mis à jour: {instrument.asset_class}')
                elif instrument.asset_class.lower() == 'index':
                    print(f'  ℹ️  Déjà en index')
                else:
                    print(f'  ⚠️  Asset class actuel: "{instrument.asset_class}" (non modifié)')
            else:
                print(f'\n⚠️  Instrument "{symbol}" non trouvé')
        
        if updated_count > 0:
            db.commit()
            print(f'\n✅ {updated_count} instrument(s) mis à jour avec succès')
        else:
            print('\nℹ️  Aucune mise à jour nécessaire')
            
        # Vérifier le résultat
        index_instruments = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.asset_class.ilike('index')
        ).all()
        
        print(f'\n📊 Instruments INDEX après mise à jour: {len(index_instruments)}')
        for inst in index_instruments:
            print(f'  - {inst.symbol}')
            
    except Exception as e:
        db.rollback()
        print(f'❌ Erreur lors de la mise à jour: {e}')
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🔄 Reclassement des indices boursiers...")
    fix_index_asset_class()
    print("✅ Terminé")

