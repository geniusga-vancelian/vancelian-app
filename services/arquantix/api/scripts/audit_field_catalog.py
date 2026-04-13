"""
Audit field_definitions catalog and generate reports
"""
import sys
from pathlib import Path

# Add api directory to path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

from database import SessionLocal, FieldDefinition
from collections import Counter
import json

EXPECTED_SLUGS = [
    "residential-address-postal-code",
    "mailing-address-postal-code",
    "id-document-type",
    "id-document-front-file",
    "id-document-selfie-file",
    "proof-of-address-file",
    "consent-kyc-processing",
    "consent-data-sharing-providers",
    "terms-accepted-at",
    "privacy-policy-accepted-at",
    "tax-residency-country-primary",
    "tax-identification-number",
    "nationality-primary",
]

IMPORTANT_CATEGORIES = ["identity", "contact", "address", "tax", "consents", "documents"]


def generate_aliases(slug: str) -> list[str]:
    """Generate alias candidates for a slug"""
    aliases = []
    slug_lower = slug.lower()
    
    # Direct variations
    aliases.append(slug_lower.replace("-", " "))
    aliases.append(slug_lower.replace("-", "_"))
    
    # Reverse: add "address" token for residential/mailing slugs
    # e.g., residential-postal-code -> residential-address-postal-code
    if "residential" in slug_lower and "address" not in slug_lower:
        # Insert "address" after "residential"
        parts = slug_lower.split("-")
        if parts[0] == "residential":
            aliases.append("-".join([parts[0], "address"] + parts[1:]))
    if "mailing" in slug_lower and "address" not in slug_lower:
        parts = slug_lower.split("-")
        if parts[0] == "mailing":
            aliases.append("-".join([parts[0], "address"] + parts[1:]))
    
    # Drop common tokens
    tokens = slug_lower.split("-")
    if "address" in tokens:
        aliases.append("-".join(t for t in tokens if t != "address"))
    if "residential" in tokens:
        aliases.append("-".join(t for t in tokens if t != "residential"))
    if "mailing" in tokens:
        aliases.append("-".join(t for t in tokens if t != "mailing"))
    
    # Common synonyms
    if "postal-code" in slug_lower or "postal_code" in slug_lower:
        aliases.append(slug_lower.replace("postal-code", "zip-code"))
        aliases.append(slug_lower.replace("postal-code", "zip"))
    if "tax-id" in slug_lower:
        aliases.append(slug_lower.replace("tax-id", "tin"))
        aliases.append(slug_lower.replace("tax-id", "nif"))
    if "nationality" in slug_lower:
        aliases.append(slug_lower.replace("nationality", "citizenship"))
    if "occupation" in slug_lower:
        aliases.append(slug_lower.replace("occupation", "job-title"))
    
    # Primary variations
    if "-primary" in slug_lower:
        aliases.append(slug_lower.replace("-primary", ""))
    if slug_lower.endswith("-primary"):
        aliases.append(slug_lower[:-8])
    
    return [a for a in aliases if a and a != slug_lower]


def main():
    db = SessionLocal()
    try:
        # Query all active fields
        fields = db.query(FieldDefinition).filter(FieldDefinition.is_active == True).all()
        
        total = len(fields)
        slugs = [f.slug for f in fields]
        
        # Counts by category
        by_category = Counter(f.category for f in fields if f.category)
        
        # Counts by field_type
        by_type = Counter(f.field_type for f in fields if f.field_type)
        
        # Top slugs by important categories
        important_slugs = []
        for cat in IMPORTANT_CATEGORIES:
            cat_fields = [f for f in fields if f.category == cat]
            important_slugs.extend([f.slug for f in cat_fields[:10]])  # Top 10 per category
        
        # Limit to top 30
        important_slugs = important_slugs[:30]
        
        # Check expected slugs
        missing_expected = [s for s in EXPECTED_SLUGS if s not in slugs]
        
        # Generate alias map
        alias_map = {}
        for field in fields:
            aliases = generate_aliases(field.slug)
            for alias in aliases:
                if alias not in alias_map:  # First match wins
                    alias_map[alias] = field.slug
        
        # Limit aliases to 300
        if len(alias_map) > 300:
            # Keep most common patterns
            alias_map = dict(list(alias_map.items())[:300])
        
        # Generate catalog snapshot
        snapshot = {
            "total": total,
            "by_category": dict(by_category),
            "by_type": dict(by_type),
            "slugs": sorted(slugs),
        }
        
        # Write files
        docs_dir = api_dir.parent / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        # 1. Markdown report
        report_lines = [
            "# Field Definitions Catalog Audit",
            "",
            f"**Total Active Fields:** {total}",
            "",
            "## Counts by Category",
            "",
        ]
        for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
            report_lines.append(f"- `{cat}`: {count}")
        
        report_lines.extend([
            "",
            "## Counts by Field Type",
            "",
        ])
        for ftype, count in sorted(by_type.items(), key=lambda x: -x[1]):
            report_lines.append(f"- `{ftype}`: {count}")
        
        report_lines.extend([
            "",
            "## Top 30 Important Slugs",
            "",
        ])
        for slug in important_slugs:
            report_lines.append(f"- `{slug}`")
        
        report_lines.extend([
            "",
            "## Missing Expected Slugs",
            "",
        ])
        if missing_expected:
            for slug in missing_expected:
                report_lines.append(f"- `{slug}` ❌")
        else:
            report_lines.append("All expected slugs are present ✓")
        
        report_path = docs_dir / "field_catalog_audit.md"
        report_path.write_text("\n".join(report_lines))
        print(f"✓ Generated {report_path}")
        
        # 2. Catalog snapshot JSON
        snapshot_path = api_dir / "services" / "ai_jurisdiction_configs" / "catalog_snapshot.json"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(snapshot, indent=2))
        print(f"✓ Generated {snapshot_path}")
        
        # 3. Slug aliases JSON
        aliases_path = api_dir / "services" / "ai_jurisdiction_configs" / "slug_aliases.json"
        aliases_path.write_text(json.dumps(alias_map, indent=2, sort_keys=True))
        print(f"✓ Generated {aliases_path}")
        
        # Summary
        print(f"\nSummary:")
        print(f"  Total slugs: {total}")
        print(f"  Missing expected: {len(missing_expected)}")
        print(f"  Aliases generated: {len(alias_map)}")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
