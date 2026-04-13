"""
Seed script for field_definitions table
Reads from api/data/field_definitions_master.csv
Idempotent: upserts by slug, updates field_name_en/field_type/category/is_active if they differ
Generates UUIDv4 for new rows only
"""
import sys
import os
import csv
from pathlib import Path

# Add api directory to path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

from database import SessionLocal, FieldDefinition
import uuid

CSV_PATH = api_dir / "data" / "field_definitions_master.csv"


def seed_field_definitions():
    """
    Seed field_definitions table from CSV.
    Idempotent: updates existing rows by slug, creates new ones.
    """
    if not CSV_PATH.exists():
        print(f"❌ Error: CSV file not found: {CSV_PATH}")
        sys.exit(1)
    
    db = SessionLocal()
    try:
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                slug = row['slug'].strip()
                field_name_en = row['field_name_en'].strip()
                field_type = row['field_type'].strip()
                category = row['category'].strip()
                is_active = row['is_active'].strip().lower() == 'true'
                
                # Check if field exists by slug
                existing = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
                
                if existing:
                    # Update if any field differs
                    needs_update = (
                        existing.field_name_en != field_name_en or
                        existing.field_type != field_type or
                        existing.category != category or
                        existing.is_active != is_active
                    )
                    
                    if needs_update:
                        existing.field_name_en = field_name_en
                        existing.field_type = field_type
                        existing.category = category
                        existing.is_active = is_active
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    # Create new field definition
                    new_field = FieldDefinition(
                        id=uuid.uuid4(),
                        slug=slug,
                        field_name_en=field_name_en,
                        field_type=field_type,
                        category=category,
                        is_active=is_active
                    )
                    db.add(new_field)
                    created_count += 1
        
        db.commit()
        
        # Verification
        total_rows = db.query(FieldDefinition).count()
        unique_slugs = db.query(FieldDefinition.slug).distinct().count()
        
        top_10 = db.query(FieldDefinition.slug).order_by(FieldDefinition.slug).limit(10).all()
        top_10_slugs = [row[0] for row in top_10]
        
        print(f"✅ Seeding complete:")
        print(f"   inserted={created_count} updated={updated_count} skipped={skipped_count}")
        print(f"   Total rows: {total_rows}")
        print(f"   Unique slugs: {unique_slugs}")
        print(f"   Top 10 slugs: {', '.join(top_10_slugs)}")
        
        if total_rows != unique_slugs:
            print(f"❌ Error: Duplicate slugs detected!")
            sys.exit(1)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_field_definitions()
