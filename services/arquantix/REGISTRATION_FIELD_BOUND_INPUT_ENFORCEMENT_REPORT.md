# Registration Field-Bound Input Enforcement

## Executive Summary

Registration builder components are now explicitly split into **content** (marketing / legal / editorial, no client binding) and **field-bound** (inputs that collect client data). Field-bound types require a `field_definition_id` and a `binding_slug` that matches the field definition slug. The admin API enforces this on create and update; publish remains gated by `check_flow_health`, which treats binding violations as **blocking errors** (not warnings). The flow editor UI guides admins through **Add Client Field** (catalog first) vs **Add Content Block**.

## Component Type Classification

Single source of truth: `api/services/registration/governance.py`.

- **`CONTENT_COMPONENT_TYPES`**: `section_title`, `rich_text`, `info_box`, `legal_content`, `divider`, `spacer`, `bullet_list`, `link_text`.
- **`INPUT_COMPONENT_TYPES`** (field-bound / compliance inputs): `text_input`, `phone_input`, `select`, `country_picker`, `date_picker`, `checkbox`, `multi_select`.

`get_component_support_registry()` adds a `family` field per type: `"content"` or `"field_bound"`.  
`GET /api/admin/registration/component-families` returns `{ "content": [...], "field_bound": [...] }`.

## Backend Enforcement

- **`validate_component_family(component_type, field_definition_id, binding_slug, db)`**  
  Raises `HTTPException(422)` when rules are violated. Loads `FieldDefinition` to verify slug alignment (hyphen/underscore normalized).

- **`create_component`** / **`update_component`** in `admin_router.py` call `validate_component_family` before persisting.

- **`check_flow_health`** (`_check_components`):  
  - Field-bound: errors if missing `field_definition_id`, missing `binding_slug`, or slug mismatch vs linked definition.  
  - Content: errors if `binding_slug` or `field_definition_id` is set.

## Admin Builder Changes

File: `web/src/app/admin/registration/flows/[id]/edit/page.tsx`.

- **+ Client Field** (default path): choose row from Field Catalog first, then optional widget type override; `binding_slug` read-only when creating from catalog; payload sends `field_definition_id` + matching `binding_slug`.
- **+ Content Block**: only content types in the selector; `binding_slug` and `field_definition_id` sent as `null` on save.
- Component list shows badges **Client Field** vs **Content**.
- Edit mode restores `field_definition_id` from API so PATCH stays valid.

## Health Check Changes

Category **`field_binding`** errors block publication (with existing publish guard). Prior overlapping consistency checks were folded into `_check_components` as hard errors.

## Tests Added

- **`tests/test_registration_governance.py`**: `TestValidateComponentFamily` (mock DB), `TestCheckFlowHealthFieldBinding` (DB fixtures), registry entries include `family`.
- **`tests/test_registration_api.py`**: content create OK without binding; input rejected without FD / with wrong slug; content rejected with binding; input OK with FD; publish returns **422** when an orphan input exists on the flow; `test_create_flow_and_publish` seeds step + screen so health allows publish.

## Backward Compatibility Notes

- **Existing rows** in `registration_screen_components` that predate enforcement may fail health checks or block publish until each input is linked to a `field_definition` and `binding_slug` is aligned. Content rows must have `binding_slug` and `field_definition_id` cleared.
- **Direct DB seeds** in tests that only set `binding_slug` without `field_definition_id` should be updated for flows that must publish; runtime-only tests may still insert legacy shapes if they never hit publish or health.
- **Flutter / runtime** unchanged: still driven by serialized components; no runtime engine refactor.

## Remaining Gaps

- No automatic migration to attach `field_definition_id` to historical components (operational data fix).
- Unknown `component_type` values skip `validate_component_family` but are still caught as errors in health.
- `link_text` remains content-only in governance; Flutter support flag unchanged.
