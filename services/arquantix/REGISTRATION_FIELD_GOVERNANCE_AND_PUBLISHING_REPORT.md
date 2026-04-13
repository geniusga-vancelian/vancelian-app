# Registration Field Governance & Publishing Report

## Executive Summary

This phase implements three governance axes for the Registration Builder:

1. **Field Definition Governance** — Administrable field catalog with usage tracking, consistency checks, and component creation from field definitions.
2. **Rules UI** — Visual editors for visibility, validation, and completion rules on steps and components, with simple form mode and raw JSON fallback.
3. **Publishing UX** — Health check system, pre-publish validation guard, publish/archive buttons, and a collapsible health panel with categorised errors and warnings.

All changes are **incremental** — no breaking changes to the runtime engine, existing APIs, or Flutter rendering. The existing architecture is preserved and enriched.

---

## Field Definition Governance

### Field Catalog Admin Page

**Route:** `/admin/registration/field-definitions`

- Searchable, filterable table of all field definitions
- Columns: slug, label, type, category, default component, required, usage count, status
- Filters: by field_type, by category, by keyword search
- Link to detail page for each field

### Field Definition Detail Page

**Route:** `/admin/registration/field-definitions/[id]`

- Complete field metadata view (slug, name, type, category, options)
- Editable metadata: ui_label, component_type_default, required_default, is_active
- Usage table showing all flows/steps/screens/components using this field
- Direct link to edit the flow from the usage table

### Component Creation from Field Catalog

In the flow editor, when adding a component:

- **Mode toggle:** "Custom" (default) or "From Field Catalog"
- Field catalog mode shows a dropdown of all active field definitions
- Selecting a field auto-populates: binding_slug, component_type, label, required, options
- The `field_definition_id` is passed to the API for proper linking

### Field Consistency Checks

The health checker detects:

- `field_definition_id` set but `binding_slug` doesn't match the field's slug → warning
- Input component has `binding_slug` but no `field_definition_id` → warning
- Content component with unnecessary `binding_slug` → warning
- Duplicate `binding_slug` on the same screen → warning

---

## Rules UI

### Visibility Rule Editor

Available on **steps** (visibility_rule_json) and **components** (visibility_rule_json).

**Two modes:**

1. **Simple mode** — Three inline fields: `field`, `operator` dropdown, `value`
2. **JSON mode** — Raw JSON textarea for complex rules (all_of, any_of)

**Supported operators:** equals, not_equals, in, not_in, exists, not_exists

### Completion Rule Editor

Available on **steps** (completion_rule_json). Same UI as visibility rules.

### Validation Rule Editor

Support for `validation_rule_json` on components via the API (field already in ComponentCreate/ComponentUpdate schemas).

### Rule Summary

When a rule is defined, a human-readable summary is displayed:
- "country = FR"
- "employment_status exists"
- "all_of(2 rules)"

---

## Publish Health Checks

### Health Check Endpoint

**`GET /api/admin/registration/flows/{flow_id}/health`**

Returns:
```json
{
  "can_publish": true,
  "errors": [],
  "warnings": [],
  "error_count": 0,
  "warning_count": 0
}
```

### Blocking Errors (prevent publication)

| Check | Category |
|-------|----------|
| Flow has no steps | structure |
| Step has no screens | structure |
| Screen has no content and no components | structure |
| Unknown component_type | component |
| Input component without binding_slug or field_definition_id | component |
| select/multi_select with no or invalid options | component |
| Flow has no jurisdiction | jurisdiction |
| Jurisdiction is inactive | jurisdiction |

### Non-blocking Warnings

| Check | Category |
|-------|----------|
| Missing i18n translation (en/fr) on step title | i18n |
| Missing i18n translation on screen title | i18n |
| Missing i18n translation on component label | i18n |
| Duplicate binding_slug on screen | consistency |
| binding_slug doesn't match field definition slug | consistency |
| Input has binding_slug but no field_definition_id | consistency |
| Content component has unnecessary binding_slug | component |
| Component type may not be supported in Flutter | flutter |
| Invalid rule JSON structure | rules |
| Unknown rule operator | rules |
| Missing field in rule | rules |

### Publish Guard

The `POST /flows/{id}/publish` endpoint now runs health checks before publishing. If there are blocking errors, it returns `422` with the error list. Warnings alone do not block publication.

### Health Panel in Admin

Collapsible panel at the top of the flow editor showing:
- Publish readiness badge (Ready / Not Ready)
- Categorised errors (red) with badges
- Categorised warnings (yellow) with scrollable list
- Auto-refreshes after component/step saves

### Publish & Archive Buttons

- **Publish** button (green) — visible when flow is in `draft` status, disabled if health check fails
- **Archive** button (orange) — visible when flow is `active`, with confirmation modal

---

## i18n Completeness

- Health checks verify translations for `en` and `fr` on:
  - Step titles
  - Screen titles
  - Component labels (input types only)
- Missing translations appear as warnings in the health panel
- Badges on the health panel categorise i18n issues

---

## Admin UX Changes

| Area | Change |
|------|--------|
| Registration index page | Added "Field Definitions Catalog" link button |
| Flow editor header | Added Health button, Publish/Archive buttons with status badge |
| Flow editor - Steps | Rule editors for visibility and completion rules |
| Flow editor - Components | Field catalog picker mode, field_definition_id propagation |
| Health panel | Collapsible panel with errors/warnings by category |
| Confirmation modals | All delete actions use AlertDialog (not browser confirm) |

---

## Tests Added

**File:** `api/tests/test_registration_governance.py` — 21 tests

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestSummarizeRule | 8 | Rule summary for all operators (equals, not_equals, in, exists, all_of, any_of, none, empty) |
| TestComponentSupportRegistry | 4 | Registry structure, input/content classification, Flutter support |
| TestHealthReport | 5 | Default state, error blocks publish, warning allows publish, serialisation, optional fields |
| TestConstants | 3 | Input/content type disjointness, union integrity, operator set |

---

## API Endpoints Added/Modified

| Method | Path | Status |
|--------|------|--------|
| GET | `/api/admin/registration/field-definitions` | **New** — List with filters and usage counts |
| GET | `/api/admin/registration/field-definitions/{id}` | **New** — Detail with usage list |
| PATCH | `/api/admin/registration/field-definitions/{id}` | **New** — Update metadata |
| GET | `/api/admin/registration/flows/{id}/health` | **New** — Health check report |
| GET | `/api/admin/registration/component-support` | **New** — Component type registry |
| POST | `/api/admin/registration/screens/{id}/components` | **Modified** — Added `field_definition_id` |
| PATCH | `/api/admin/registration/components/{id}` | **Modified** — Added `field_definition_id` |
| POST | `/api/admin/registration/flows/{id}/publish` | **Modified** — Health check guard |

---

## Files Created/Modified

### Created

| File | Purpose |
|------|---------|
| `api/services/registration/governance.py` | Governance service (health checks, consistency, i18n, rules, registry) |
| `api/tests/test_registration_governance.py` | 21 unit tests for governance |
| `web/src/app/admin/registration/field-definitions/page.tsx` | Field catalog admin page |
| `web/src/app/admin/registration/field-definitions/[id]/page.tsx` | Field detail admin page |

### Modified

| File | Changes |
|------|---------|
| `api/services/registration/admin_router.py` | New endpoints, field_definition_id in schemas, publish guard |
| `web/src/app/admin/registration/flows/[id]/edit/page.tsx` | Health panel, publish/archive, field catalog picker, RuleEditor component |
| `web/src/app/admin/registration/page.tsx` | Link to field definitions |

---

## Backward Compatibility Notes

- **No breaking changes** to the runtime engine
- **No migration required** — all new fields use existing columns (field_definition_id already exists on components)
- **Existing admin flows continue to work** — new features are additive
- **Flutter rendering unaffected** — governance is admin-side only
- **Publish guard is the only behavioral change** — flows with blocking errors can no longer be published

---

## Remaining Gaps / Next Steps

1. **Validation rule UI on components** — The `validation_rule_json` field is wired in the API but no UI editor is displayed yet in the component form (simple to add with the same `RuleEditor` component)
2. **i18n completeness badges** — Currently shown as warnings in health panel; could add inline badges per component/step in the editor
3. **Field definition CRUD** — Creating new field definitions from the admin (currently read + edit only)
4. **Component preview for link_text** — The preview page doesn't render link_text components
5. **Bulk i18n export/import** — For large-scale translation workflows
6. **Audit trail** — Track who modified field definitions and flow configurations
7. **Role-based access** — Admin actions should eventually require authentication
