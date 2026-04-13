#!/usr/bin/env python3
"""
Script pour supprimer les instruments Alpha Vantage de la base de données.
Ne conserve que les instruments Yahoo Finance.

Usage: python3 api/scripts/cleanup_alphavantage_instruments.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import SessionLocal, MarketDataInstrument, MarketDataBarD1, BacktestInstrumentSeries
from sqlalchemy import and_

def cleanup_alphavantage_instruments():
    """
    Nettoie les instruments Alpha Vantage de la base de données.
    Stratégie:
    1. Pour les instruments qui correspondent à des symboles CORE_V1: mettre à jour le provider à "yahoo"
    2. Pour les autres instruments Alpha Vantage: supprimer uniquement s'ils ne sont pas référencés par des backtests
    """
    from services.market_data.routes import CORE_V1_INSTRUMENTS
    
    db = SessionLocal()
    try:
        core_symbols = {inst["symbol"] for inst in CORE_V1_INSTRUMENTS}
        
        # 1. Identifier les instruments Alpha Vantage
        alphavantage_instruments = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.provider != "yahoo"
        ).all()
        
        if not alphavantage_instruments:
            print("✅ Aucun instrument Alpha Vantage trouvé. Tous les instruments sont déjà Yahoo Finance.")
            return
        
        print(f"⚠️  Trouvé {len(alphavantage_instruments)} instrument(s) Alpha Vantage:")
        
        # 2. Séparer les instruments CORE_V1 (à mettre à jour) des autres (à supprimer si possible)
        to_update = []
        to_delete = []
        
        for inst in alphavantage_instruments:
            if inst.symbol in core_symbols:
                to_update.append(inst)
                print(f"   - {inst.symbol} (ID: {inst.id}, provider: {inst.provider}) -> MISE À JOUR vers yahoo")
            else:
                to_delete.append(inst)
                print(f"   - {inst.symbol} (ID: {inst.id}, provider: {inst.provider}) -> SUPPRESSION")
        
        # 3. Mettre à jour les instruments CORE_V1
        if to_update:
            instrument_ids_update = [inst.id for inst in to_update]
            
            # Supprimer les bars Alpha Vantage associés
            bars_deleted = db.query(MarketDataBarD1).filter(
                MarketDataBarD1.instrument_id.in_(instrument_ids_update)
            ).delete(synchronize_session=False)
            if bars_deleted > 0:
                print(f"✅ {bars_deleted} bar(s) D1 supprimé(s) pour les instruments CORE_V1")
            
            # Mettre à jour le provider
            db.query(MarketDataInstrument).filter(
                MarketDataInstrument.id.in_(instrument_ids_update)
            ).update({"provider": "yahoo"}, synchronize_session=False)
            print(f"✅ {len(to_update)} instrument(s) CORE_V1 mis à jour vers provider='yahoo'")
        
        # 4. Supprimer les autres instruments Alpha Vantage (s'ils ne sont pas référencés)
        if to_delete:
            instrument_ids_delete = [inst.id for inst in to_delete]
            
            # Vérifier les références dans backtest_instrument_series
            referenced_ids = db.query(BacktestInstrumentSeries.instrument_id).filter(
                BacktestInstrumentSeries.instrument_id.in_(instrument_ids_delete)
            ).distinct().all()
            referenced_ids_set = {row[0] for row in referenced_ids}
            
            # Ne supprimer que ceux qui ne sont pas référencés
            safe_to_delete = [inst for inst in to_delete if inst.id not in referenced_ids_set]
            safe_to_delete_ids = [inst.id for inst in safe_to_delete]
            
            if safe_to_delete_ids:
                # Supprimer les bars associés
                bars_deleted = db.query(MarketDataBarD1).filter(
                    MarketDataBarD1.instrument_id.in_(safe_to_delete_ids)
                ).delete(synchronize_session=False)
                if bars_deleted > 0:
                    print(f"✅ {bars_deleted} bar(s) D1 supprimé(s) pour les instruments non-CORE_V1")
                
                # Supprimer les instruments
                db.query(MarketDataInstrument).filter(
                    MarketDataInstrument.id.in_(safe_to_delete_ids)
                ).delete(synchronize_session=False)
                print(f"✅ {len(safe_to_delete)} instrument(s) Alpha Vantage non-CORE_V1 supprimé(s)")
            
            if len(referenced_ids_set) > 0:
                warning_ids = [inst.id for inst in to_delete if inst.id in referenced_ids_set]
                print(f"⚠️  {len(warning_ids)} instrument(s) Alpha Vantage non supprimé(s) car référencé(s) par des backtests: {warning_ids}")
                print(f"   (Ces instruments seront mis à jour lors de la prochaine initialisation)")
        
        db.commit()
        
        # 5. Vérifier qu'il reste des instruments Yahoo Finance
        yahoo_count = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.provider == "yahoo"
        ).count()
        
        print(f"✅ Il reste {yahoo_count} instrument(s) Yahoo Finance dans la base")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors du nettoyage: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║     NETTOYAGE INSTRUMENTS ALPHA VANTAGE                                   ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
    print("")
    cleanup_alphavantage_instruments()
    print("")
    print("✅ Nettoyage terminé avec succès")
