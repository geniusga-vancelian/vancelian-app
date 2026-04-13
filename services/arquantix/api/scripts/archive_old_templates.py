"""
Script to archive old email templates
Marks all templates except arquantix_ugg_v1_db as DRAFT (archived)
This is a non-destructive operation - templates are not deleted
"""
import sys
from pathlib import Path

# Add api directory to path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

from database import SessionLocal, EmailTemplateEntity, EmailStatusEnum


def archive_old_templates():
    """Archive all templates except arquantix_ugg_v1_db"""
    db = SessionLocal()
    try:
        # Find all templates
        all_templates = db.query(EmailTemplateEntity).all()
        
        archived_count = 0
        kept_count = 0
        
        for template in all_templates:
            # Keep only arquantix_ugg_v1_db (or arquantix_ugg_v1 if it exists)
            if template.slug in ["arquantix_ugg_v1_db", "arquantix_ugg_v1"]:
                print(f"✅ Keeping template: {template.slug} ({template.name})")
                kept_count += 1
            else:
                # Archive by setting status to DRAFT
                old_status = template.status
                template.status = EmailStatusEnum.DRAFT
                print(f"📦 Archiving template: {template.slug} ({template.name}) - Status: {old_status} -> DRAFT")
                archived_count += 1
        
        db.commit()
        
        print(f"\n✅ Archive complete:")
        print(f"   - Kept: {kept_count} template(s)")
        print(f"   - Archived: {archived_count} template(s)")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    print("🔄 Archiving old email templates...")
    print("   (Setting status to DRAFT for all except arquantix_ugg_v1_db)\n")
    archive_old_templates()






