# Client Identity Hardening — Phase 1B Report

## Executive Summary

Phase 1B hardens the client identity system introduced in Phase 1A across three axes:

1. **Authentication layer** — All identity/KYC endpoints now require JWT authentication with ownership checks.
2. **KYC status cleanup** — The ambiguous `pending_review → in_progress` mapping is replaced by a 1:1 direct mapping.
3. **Eligibility engine** — A centralized `EligibilityService` replaces scattered eligibility checks.

**Result:** 85 tests pass (34 new + 51 updated), 0 regressions on portfolio engine tests (31/31 pass).

---

## Auth Implementation

### Architecture

Reuses the existing JWT system (`auth.py` + `AdminUser`) and extends it with identity-aware context.

**New files:**

| File | Purpose |
|------|---------|
| `services/auth/__init__.py` | Package init |
| `services/auth/models.py` | `AuthContext` model (user_id, email, role, person_id, client_id) |
| `services/auth/dependencies.py` | FastAPI dependencies for auth + ownership |

### Dependencies

| Dependency | Behavior |
|------------|----------|
| `get_current_user_or_admin` | Decode JWT, resolve user from `admin_users`, resolve linked person/client. Returns `AuthContext`. 401 if missing/invalid. |
| `require_admin` | Wraps `get_current_user_or_admin`, enforces `role == "admin"`. 403 if not. |
| `require_person_access(person_id)` | Owner (matching person_id) or admin. 403 otherwise. |
| `require_client_access_identity(client_id)` | Owner (matching client_id) or admin. 403 otherwise. |

### Protected Endpoints

| Endpoint | Guard |
|----------|-------|
| `POST /api/persons` | `require_admin` |
| `GET /api/persons/{id}/identity` | `require_person_access` (owner or admin) |
| `PATCH /api/persons/{id}/kyc-status` | `require_admin` |
| `POST /api/persons/{id}/link-client` | `require_admin` |
| `GET /api/portfolio-engine/clients/{id}/identity` | `require_client_access_identity` (owner or admin) |

### Backward Compatibility

- `GET /api/persons/{id}` — **unchanged** (no auth required, backward-compatible)
- `POST /api/persons/{id}/fields` — **unchanged** (no auth required)
- All PE endpoints — **unchanged** (use existing ActorContext / header-based auth)

---

## KYC Status Fix

### Problem

The Phase 1A mapping downgraded `pending_review` to `in_progress` on the client side:

```
persons.kyc_status = "pending_review"
  → pe_clients.kyc_status = "in_progress"  ← AMBIGUOUS
```

This caused confusion: the client couldn't distinguish between "documents submitted, waiting for review" and "actively collecting documents".

### Fix

**Code change** in `services/client_identity/service.py`:

```python
# BEFORE
_PERSON_TO_CLIENT_KYC_MAP = {
    "pending_review": "in_progress",  # ambiguous
}

# AFTER
_PERSON_TO_CLIENT_KYC_MAP = {
    "pending_review": "pending_review",  # 1:1 direct
}
```

The `KycStatus` enum in `services/portfolio_engine/clients/enums.py` already had `PENDING_REVIEW` (added in Phase 1A). The `pe_clients.kyc_status` column is `String(30)`, not a PostgreSQL enum, so no schema change is needed.

### Migration 083

**File:** `alembic/versions/083_fix_pending_review_kyc_sync.py`

Corrects existing data:

```sql
UPDATE pe_clients SET kyc_status = 'pending_review'
FROM persons
WHERE pe_clients.person_id = persons.id
  AND persons.kyc_status = 'pending_review'
  AND pe_clients.kyc_status = 'in_progress'
```

Reversible: downgrade restores `in_progress`.

### KYC Status Matrix (Final)

| persons.kyc_status | pe_clients.kyc_status |
|--------------------|-----------------------|
| not_started | not_started |
| in_progress | in_progress |
| pending_review | **pending_review** |
| approved | approved |
| rejected | rejected |

---

## Eligibility Engine

### Architecture

**New files:**

| File | Purpose |
|------|---------|
| `services/compliance/__init__.py` | Package init |
| `services/compliance/eligibility_service.py` | `EligibilityService` + `EligibilityResult` |

### EligibilityResult

```python
@dataclass
class EligibilityResult:
    eligible: bool      # AND of all criteria
    reasons: list[str]  # human-readable failure reasons
    kyc_ok: bool        # person.kyc_status == "approved"
    aml_ok: bool        # True (placeholder for Sumsub Phase 2)
    risk_ok: bool       # risk_tier != "high"
```

### V1 Rules

| Criterion | Rule | Source |
|-----------|------|--------|
| `kyc_ok` | `person.kyc_status == "approved"` | `persons.kyc_status` |
| `aml_ok` | Always `True` | Placeholder — Sumsub in Phase 2 |
| `risk_ok` | `risk_tier != "high"` | `persons.profile_json["risk-tier-current"]` |
| `eligible` | `kyc_ok AND aml_ok AND risk_ok` | Derived |

### Integration

| Location | Before | After |
|----------|--------|-------|
| `client_identity/service.py` `is_client_eligible_for_products()` | Inline KYC + risk check | Delegates to `EligibilityService.evaluate_by_person_id()` |
| `provisioning/service.py` `_validate_client_eligible()` | Inline person.kyc_status check | Delegates to `EligibilityService.evaluate_client_eligibility()` |
| `persons/routes.py` `GET /identity` | Simple `is_eligible` boolean | Full `EligibilityDetail` in response |

### API Response Enrichment

`GET /api/persons/{id}/identity` now returns:

```json
{
  "eligibility": {
    "eligible": true,
    "kyc_ok": true,
    "aml_ok": true,
    "risk_ok": true,
    "reasons": []
  }
}
```

### Audit

Each eligibility evaluation creates an `AuditEvent` with `event_type = "CLIENT_ELIGIBILITY_EVALUATED"` containing the full result.

---

## Tests Added

### New Test Files (Phase 1B)

| File | Tests | Coverage |
|------|-------|----------|
| `test_auth_identity.py` | 10 | No-token 401, bad-token 401, admin creates person, admin reads identity, admin updates KYC, admin reads client identity |
| `test_kyc_status_clean.py` | 9 | pending_review stays pending_review, full lifecycle, parametrized all 5 statuses |
| `test_eligibility_engine.py` | 15 | approved OK, all non-approved KO, high risk KO, medium risk OK, no risk OK, combined failures, person not found, audit event created, audit payload verified |

### Updated Tests (from Phase 1A)

| File | Change |
|------|--------|
| `test_client_identity_api.py` | Added auth headers to all API calls |
| `test_client_identity_service.py` | Updated `test_pending_review_maps_to_in_progress` → `test_pending_review_maps_to_pending_review` |
| `test_client_identity_kyc_sync.py` | Updated lifecycle expectations: `pending_review → pending_review` |
| `conftest.py` | Added `make_admin_headers()` helper, forced `Client` mapper init |

### Test Results

```
85 passed (identity suite)
31 passed (portfolio engine non-regression)
0 failed
```

---

## Migration Notes

| Migration | Description | Reversible |
|-----------|-------------|-----------|
| 083 | Fix pe_clients where pending_review was stored as in_progress | Yes |

---

## Remaining Risks / Next Steps

| Item | Status | Notes |
|------|--------|-------|
| AML check (Sumsub) | Placeholder `True` | Wire in Phase 2 |
| Exchange endpoints | No KYC guard | Document as Phase 2 task |
| Lending endpoints | No KYC guard | Document as Phase 2 task |
| User-facing JWT (non-admin) | Prepared | `AuthContext.role` supports "user", ownership checks ready |
| RBAC extension | Prepared | `is_admin` property exists, extendable to more roles |
| `GET /api/persons/{id}` auth | Not wired | Kept open for backward-compat |
| `POST /api/persons/{id}/fields` auth | Not wired | Kept open for backward-compat |

---

## Files Changed

### Created

- `api/services/auth/__init__.py`
- `api/services/auth/models.py`
- `api/services/auth/dependencies.py`
- `api/services/compliance/__init__.py`
- `api/services/compliance/eligibility_service.py`
- `api/alembic/versions/083_fix_pending_review_kyc_sync.py`
- `api/tests/test_auth_identity.py`
- `api/tests/test_kyc_status_clean.py`
- `api/tests/test_eligibility_engine.py`

### Modified

- `api/services/client_identity/service.py` — KYC mapping fix + eligibility delegation
- `api/services/persons/routes.py` — Auth wiring + eligibility response enrichment
- `api/services/portfolio_engine/clients/router.py` — Auth wiring on /identity
- `api/services/portfolio_engine/provisioning/service.py` — EligibilityService delegation
- `api/tests/conftest.py` — `make_admin_headers()` + Client mapper init
- `api/tests/test_client_identity_api.py` — Auth headers
- `api/tests/test_client_identity_service.py` — pending_review expectation
- `api/tests/test_client_identity_kyc_sync.py` — pending_review expectation
