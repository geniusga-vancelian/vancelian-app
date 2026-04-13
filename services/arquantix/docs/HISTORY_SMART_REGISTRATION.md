# Smart Registration & Compliance Engine — History

## 1. Project Goal
- **Problem**: Multi-jurisdiction client onboarding with full audit trail and configurable compliance rules
- **Core principles**:
  - Audit-first: All field changes traceable via `audit_events` (append-only)
  - Config-driven: Onboarding flows and AML rules defined in `jurisdiction_configs` (versioned, publishable)
  - Multi-jurisdiction: Same engine supports EU, UAE, US, FR with different rules
  - State cache: `persons.profile_json` is derived state, not source of truth (replayable from audit)

## 2. Final Architecture (as of today)
- **Backend**: FastAPI (Python) on port 8000
- **Frontend**: Next.js App Router (TypeScript) on port 3000
- **Database**: PostgreSQL (arquantix-db on port 5443)
- **Key concepts**:
  - `field_definitions`: Master catalog of client identity fields (slug, type, category)
  - `persons.profile_json`: JSONB state cache (derived from audit events)
  - `audit_events`: Append-only event log (FIELD_SET, AML_RISK_COMPUTED, etc.)
  - `jurisdiction_configs`: Versioned configs (KYC onboarding flows, AML risk rules)
  - **Onboarding engine**: Runtime step evaluator with condition-based block visibility
  - **AML risk engine**: Rules-based scoring with explainable flags/actions/tiers

## 3. Database State
- **Alembic**: Single head at revision `010` (current: `010`)
- **Tables created**:
  - `field_definitions` (id, slug, field_name_en, field_type, category, is_active, timestamps)
  - `persons` (id, status, jurisdiction, profile_json, timestamps)
  - `audit_events` (id, person_id, event_type, actor_type, actor_id, correlation_id, payload, schema_version, created_at)
  - `jurisdiction_configs` (id, jurisdiction, purpose, version, status, config_json, timestamps)
  - `documents` (id, person_id, doc_type, status, storage_provider, storage_bucket, storage_key, content_type, file_size, sha256, metadata_json, timestamps)
- **Field catalog**: 122 fields, 122 unique slugs (all active)
- **Indexes**: GIN on JSONB columns, btree on category/jurisdiction/status, composite indexes on (person_id, created_at)

## 4. Backend Features Implemented
- **FIELD_SET flow** (`api/services/person_fields/service.py`):
  - Accepts `person_id`, `field_id` (slug), `value`
  - Writes `audit_event` with type `FIELD_SET` and payload
  - Projects value into `persons.profile_json[slug]`
  - Atomic transaction (rollback on error)
  - No silent overwrite (always creates audit event)
- **Jurisdiction configs CRUD + publish** (`api/services/jurisdiction_configs/`):
  - Create/read/update draft configs
  - Publish endpoint: sets config `status=active`, archives previous active for same (jurisdiction, purpose)
  - Publish-time validation: verifies all referenced field slugs exist and are active
  - AML tier validation: ensures full score range coverage, no gaps, no overlaps
- **Onboarding engine** (`api/services/onboarding/`):
  - `GET /api/persons/{id}/onboarding/next-step`: Evaluates conditions, returns next incomplete step
  - `POST /api/persons/{id}/onboarding/submit-step`: Validates fields, calls FIELD_SET for each, returns next step
  - Condition evaluator: supports `equals`, `not_equals`, `in`, `not_in`, `exists`, `not_exists`
  - Atomic step submission (all fields in single transaction)
- **AML risk engine** (`api/services/aml_risk/`):
  - `POST /api/persons/{id}/risk/compute`: Loads active AML config, evaluates rules, computes score
  - Rules: `when` (condition), `effect` (add_score, set_flag, require_action, stop, weight)
  - Bounding: enforces min_score ≤ score ≤ max_score
  - Tier resolution: maps score to tier from config outputs
  - Writes `AML_RISK_COMPUTED` audit event
  - Projects derived fields: `risk-score-current`, `risk-tier-current`, `aml-flags`, `aml-required-actions`
- **Documents + audit trail**: Table created, storage provider abstraction (S3/R2), no binary in DB

## 5. Frontend Admin (Current State)
- **Admin UI exists**: `/admin/jurisdiction-configs`
- **Jurisdiction Config Builder**:
  - **List page** (`web/src/app/admin/jurisdiction-configs/page.tsx`):
    - Filters: jurisdiction, purpose, status
    - Search by jurisdiction/purpose/status
    - Card grid with status badges
  - **Edit/Create page** (`web/src/app/admin/jurisdiction-configs/[id]/page.tsx`):
    - Basic info: jurisdiction (select), purpose (KYC/AML_RISK), version/status (read-only)
    - Save (create/update draft)
    - Publish button (calls publish endpoint)
  - **KYC Builder** (`web/src/components/admin/KYCBuilder.tsx`):
    - Steps → Blocks → Fields hierarchy
    - Drag/drop ordering (UI exists, backend supports order)
    - Conditions editor: if/then for block visibility
    - Live preview (renders onboarding flow, no submission)
  - **AML Risk Builder** (`web/src/components/admin/AMLRiskBuilder.tsx`):
    - Rules table (orderable)
    - When condition editor
    - Effect editor (add_score, set_flag, require_action, stop, weight)
    - Tiers editor with validation preview (coverage/overlap checks)
- **Field selector** (`web/src/components/admin/FieldSelector.tsx`):
  - Queries `/api/admin/field-definitions`
  - Search by slug/name
  - Filter by category
  - Multi-select with selected chips

## 6. Known Issues / WIP (IMPORTANT)
- **Admin UI proxy routes**: Recently fixed (2025-01-12)
  - Issue: `GET /api/admin/jurisdiction-configs` returned 500
  - Root cause: Wrong API base URL (8011 vs 8000), missing JWT auth
  - Fix: Updated all proxy routes to use `API_BASE_URL` env var, generate JWT tokens
  - Files updated:
    - `web/src/app/api/admin/jurisdiction-configs/route.ts`
    - `web/src/app/api/admin/jurisdiction-configs/[id]/route.ts`
    - `web/src/app/api/admin/jurisdiction-configs/[id]/publish/route.ts`
    - `web/src/app/api/admin/field-definitions/route.ts`
- **Current blocker**: None (proxy routes fixed, backend running on 8000)
- **Must check first tomorrow**:
  1. Verify `GET /api/admin/jurisdiction-configs` returns 200 (empty list OK)
  2. Verify admin page loads configs (or shows "no configs" gracefully)
  3. Check browser console for any remaining fetch errors

## 7. Test Status
- **Pytest global status**: All core suites passing
- **Core suites** (passing):
  - `test_person_fields.py`: FIELD_SET flow, audit events, profile_json updates
  - `test_onboarding_engine.py`: Step evaluation, condition evaluation, atomic submission
  - `test_aml_risk_engine.py`: Scoring, bounding, tier resolution, audit events
  - `test_contracts.py`: Derived fields exist, single active config, AML engine contracts
  - `test_jurisdiction_configs_validation.py`: Publish-time field validation, tier validation
- **Legacy suites** (passing, unrelated):
  - `test_cppi_v1.py`, `test_core_satellite_v1.py`, `test_cppi_bundle_validation.py`: Backtest/CPPI strategy tests (fixed 2025-01-12)
- **Test isolation**: Uses `conftest.py` with transaction rollback fixture (deterministic)

## 8. Next Logical Steps
- **Immediate next task**: Verify admin UI proxy routes work end-to-end (test list/create/edit/publish)
- **Deferred tasks**:
  - Admin UX polish: Drag/drop persistence, better error messages, loading states
  - Provider integration: KYC (Sumsub/Onfido), AML screening (ComplyAdvantage)
  - Production deployment: Environment configs, secrets management, monitoring
  - Multi-head prevention: Alembic merge strategy documentation
  - Replay engine: Rebuild `profile_json` from `audit_events` (for data recovery)
