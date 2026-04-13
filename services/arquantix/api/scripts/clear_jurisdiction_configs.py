#!/usr/bin/env python3
"""
Script pour vider toutes les jurisdiction-configs de la base de données.
Usage: python3 api/scripts/clear_jurisdiction_configs.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, JurisdictionConfig
from sqlalchemy import text

def clear_all_jurisdiction_configs():
    """Supprime toutes les jurisdiction-configs de la base de données."""
    db = SessionLocal()
    try:
        # Count before deletion
        count_before = db.query(JurisdictionConfig).count()
        print(f"📊 Nombre de configs avant suppression: {count_before}")
        
        if count_before == 0:
            print("✅ Aucune config à supprimer.")
            return
        
        # Delete all configs
        deleted = db.query(JurisdictionConfig).delete()
        db.commit()
        
        print(f"✅ {deleted} jurisdiction-config(s) supprimée(s) avec succès.")
        
        # Verify deletion
        count_after = db.query(JurisdictionConfig).count()
        if count_after == 0:
            print("✅ Vérification: toutes les configs ont été supprimées.")
        else:
            print(f"⚠️  Attention: {count_after} config(s) restante(s).")
            
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la suppression: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    print("🗑️  Suppression de toutes les jurisdiction-configs...")
    print("=" * 60)
    clear_all_jurisdiction_configs()
    print("=" * 60)
    print("✅ Terminé.")
