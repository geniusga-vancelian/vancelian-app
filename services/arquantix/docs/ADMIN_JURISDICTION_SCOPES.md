# Admin UI — Jurisdiction Scopes

## Overview

The `jurisdiction` field in `jurisdiction_configs` represents a **regulatory scope identifier**, not a simple country code.

## Naming Convention

Format: `<Company>_<Region>_<Regulator>_<License?>`

Examples:
- `Arquantix_UAE_DIFC_cat4_crowdfunding` — Arquantix operating under DIFC Category 4 Crowdfunding license in UAE
- `Vancelian_UAE_VARA` — Vancelian operating under VARA regulation in UAE
- `Vancelian_EU_MICA` — Vancelian operating under MiCA regulation in EU

## Why Regulatory Scope Instead of Country?

**Problem**: A single country can have multiple regulators with different rules.

Example: UAE has both DIFC (Dubai International Financial Centre) and VARA (Virtual Assets Regulatory Authority). These are separate regulatory frameworks with different compliance requirements.

**Solution**: Use a composite identifier that includes:
1. **Company**: Which entity is operating (Arquantix vs Vancelian)
2. **Region**: Geographic region (UAE, EU, etc.)
3. **Regulator**: Specific regulatory body (DIFC, VARA, MiCA)
4. **License** (optional): Specific license type or category

This avoids confusion and ensures each config is tied to the exact regulatory framework.

## Backend Behavior

- **Database**: `jurisdiction` column is `TEXT` (no enum constraint)
- **Backend**: Accepts any non-empty string (backward compatible)
- **Validation**: Optional helper `validate_jurisdiction_format()` logs warnings but does not block
- **Existing data**: Legacy jurisdictions (e.g., "EU", "UAE") remain valid and functional

## Frontend Admin UI

### Creating/Editing Configs

The jurisdiction select shows the current regulatory scopes:
- Arquantix – UAE – DIFC – Cat 4 – Crowdfunding
- Vancelian – UAE – VARA
- Vancelian – EU – MiCA

### Legacy Jurisdictions

If an existing config has a jurisdiction not in the current list (e.g., "EU", "UAE"), the UI displays:
- **Edit page**: Yellow warning banner with "Unknown / Legacy jurisdiction (read-only)"
- **List page**: Shows the raw jurisdiction value with "(read-only)" label

Legacy configs remain functional but cannot be edited (jurisdiction field is read-only).

## Adding New Regulatory Scopes

1. Update `web/src/lib/admin/jurisdictions.ts`:
   - Add new entry to `REGULATORY_JURISDICTIONS` array
   - Follow naming convention: `<Company>_<Region>_<Regulator>_<License?>`
   - Provide human-readable label

2. No backend changes required (accepts any string)

3. No database migration required (TEXT column)

## Technical Notes

- **No breaking changes**: Existing configs with "EU", "UAE", etc. continue to work
- **No data migration**: Legacy jurisdictions remain in database as-is
- **Onboarding engine**: Unchanged (uses jurisdiction as opaque identifier)
- **AML risk engine**: Unchanged (uses jurisdiction as opaque identifier)
