# Database Schema Audit Report
**Date:** 2026-01-12  
**Scope:** 5 tables (field_definitions, persons, audit_events, jurisdiction_configs, documents)

---

## 1. field_definitions

### Migration (003_add_field_definitions.py)
✅ **PASS**
- Columns: id (UUID), slug (TEXT), field_name_en (TEXT), field_type (TEXT), category (TEXT), is_active (BOOLEAN), created_at (TIMESTAMPTZ), updated_at (TIMESTAMPTZ)
- Constraints: PK on id, UNIQUE on slug
- Indexes: btree on category
- Triggers: auto-update updated_at

### Model (database.py)
✅ **PASS**
- All columns match migration
- Index on category matches
- Schema: public ✓

### Diffs
- None

---

## 2. persons

### Migration (004_add_persons_table.py)
❌ **FAIL**
- Columns: id (UUID), status (TEXT), jurisdiction (TEXT), profile_json (JSONB)
- **MISSING:** created_at, updated_at (required per spec)
- Indexes: GIN on profile_json, btree on jurisdiction ✓
- No triggers

### Model (database.py)
❌ **FAIL**
- Columns: id, status, jurisdiction, profile_json
- **MISSING:** created_at, updated_at (required per spec)
- Indexes match migration ✓

### Diffs
- ❌ Missing `created_at` column (TIMESTAMPTZ, default now())
- ❌ Missing `updated_at` column (TIMESTAMPTZ, default now(), auto-updated)

---

## 3. audit_events

### Migration (005_add_audit_events_table.py)
✅ **PASS**
- Columns: id (UUID), person_id (UUID FK), event_type (TEXT), actor_type (TEXT), actor_id (TEXT), correlation_id (UUID), payload (JSONB), schema_version (INT), created_at (TIMESTAMPTZ)
- Constraints: PK on id, FK to persons.id with CASCADE
- Indexes: composite (person_id, created_at), event_type, correlation_id, GIN on payload
- All required columns present ✓

### Model (database.py)
✅ **PASS**
- All columns match migration
- Foreign key relationship defined ✓
- Indexes match ✓
- Schema: public ✓

### Diffs
- None

---

## 4. jurisdiction_configs

### Migration (006_add_jurisdiction_configs_table.py)
✅ **PASS**
- Columns: id (UUID), jurisdiction (TEXT), purpose (TEXT), version (INT), status (TEXT), config_json (JSONB), created_at (TIMESTAMPTZ), updated_at (TIMESTAMPTZ)
- Constraints: PK on id, UNIQUE (jurisdiction, purpose, version)
- Indexes: composite (jurisdiction, purpose, status), GIN on config_json
- Triggers: auto-update updated_at ✓

### Model (database.py)
✅ **PASS**
- All columns match migration
- UniqueConstraint matches ✓
- Indexes match ✓
- Schema: public ✓

### Diffs
- None

---

## 5. documents

### Migration (007_add_documents_table.py)
✅ **PASS**
- Columns: id (UUID), person_id (UUID FK), doc_type (TEXT), status (TEXT), storage_provider (TEXT), storage_bucket (TEXT), storage_key (TEXT), content_type (TEXT), file_size (BIGINT), sha256 (TEXT), metadata (JSONB), created_at (TIMESTAMPTZ), updated_at (TIMESTAMPTZ)
- Constraints: PK on id, FK to persons.id with CASCADE
- Indexes: composite (person_id, created_at), GIN on metadata
- Triggers: auto-update updated_at ✓

### Model (database.py)
✅ **PASS**
- All columns match migration
- Foreign key relationship defined ✓
- Indexes match ✓
- Schema: public ✓

### Diffs
- None

---

## Summary

| Table | Migration | Model | Status |
|-------|-----------|-------|--------|
| field_definitions | ✅ | ✅ | **PASS** |
| persons | ❌ | ❌ | **FAIL** (missing created_at/updated_at) |
| audit_events | ✅ | ✅ | **PASS** |
| jurisdiction_configs | ✅ | ✅ | **PASS** |
| documents | ✅ | ✅ | **PASS** |

## Required Fixes

### persons table
1. Add `created_at` column (TIMESTAMPTZ, NOT NULL, default now())
2. Add `updated_at` column (TIMESTAMPTZ, NOT NULL, default now())
3. Add trigger function and trigger for auto-updating `updated_at`
4. Update SQLAlchemy model to include these columns

---

**Next Steps:**
1. Create migration 008 to add created_at/updated_at to persons
2. Update Person model in database.py
3. Run migration
4. Proceed with seed data generation
