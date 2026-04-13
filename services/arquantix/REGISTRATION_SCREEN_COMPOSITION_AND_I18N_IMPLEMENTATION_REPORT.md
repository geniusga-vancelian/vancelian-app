# Registration Screen Composition & i18n — Implementation Report

## Executive Summary

This implementation extends the Registration Builder to support full screen composition and progressive internationalization, without breaking the existing runtime. All changes are backward-compatible.

**Delivered:**
- 5 new component types (`info_box`, `rich_text`, `divider`, `spacer`, `bullet_list`)
- Screen and component reorder in admin UI (▲▼ buttons for screens and components)
- i18n foundation with localized JSON in `props_json` and new `title_i18n`/`subtitle_i18n` columns
- Language tabs in admin builder for steps, screens, and components
- Runtime `?lang=` parameter for language-resolved API responses
- `resolveLocalized()` helper in backend with fallback chain
- Flutter renderer updated with 4 new component types
- Admin preview supporting all 14 component types
- 21 backend tests + 4 new Flutter widget tests
- Alembic migration 090 applied

---

## Quick Wins Implemented

### 1. New component types in admin builder

`COMPONENT_TYPES` extended from 9 to 14:

| Type | Category | Admin | Preview | Flutter |
|------|----------|-------|---------|---------|
| `text_input` | Input | ✅ | ✅ | ✅ |
| `phone_input` | Input | ✅ | ✅ | ✅ |
| `select` | Input | ✅ | ✅ | ✅ |
| `country_picker` | Input | ✅ | ✅ | ✅ |
| `date_picker` | Input | ✅ | ✅ | ✅ |
| `checkbox` | Input | ✅ | ✅ | ✅ |
| `multi_select` | Input | ✅ | ✅ (fixed) | ✅ |
| `section_title` | Content | ✅ | ✅ | ✅ |
| `legal_content` | Content | ✅ | ✅ | ✅ |
| `info_box` | Content | ✅ (new) | ✅ (new) | ✅ |
| `rich_text` | Content | ✅ (new) | ✅ (new) | ✅ (new) |
| `divider` | Content | ✅ (new) | ✅ (new) | ✅ (new) |
| `spacer` | Content | ✅ (new) | ✅ (new) | ✅ (new) |
| `bullet_list` | Content | ✅ (new) | ✅ (new) | ✅ (new) |

### 2. Admin sidebar link

Added "Registration" entry in `AdminSidebar.tsx` between "Vault Builder" and "Help".

### 3. Preview fixes

- `multi_select`: now renders as checkbox group (was "Unknown")
- `info_box`: blue info box with ℹ icon
- `rich_text`: prose paragraph rendering
- `divider`: horizontal rule
- `spacer`: transparent vertical space
- `bullet_list`: unordered list with title

### 4. Reorder in admin UI

- **Screens**: ▲▼ buttons wired to `POST .../screens/reorder`
- **Components**: ▲▼ buttons wired to `POST .../components/reorder`
- Steps already had reorder buttons (unchanged)

### 5. Content vs Input component UX

The admin component form adapts dynamically:
- Content types: no `binding_slug`, no `required`, show `text` textarea
- Input types: show `binding_slug`, `placeholder`, `required`
- `select`/`multi_select`: show JSON options editor
- `spacer`: show height input
- `bullet_list`: show items JSON editor
- Badge color distinguishes content (purple) from input (indigo)

---

## i18n Data Model Changes

### Migration 090

Added nullable JSONB columns:

| Table | Column | Purpose |
|-------|--------|---------|
| `registration_flow_steps` | `title_i18n` | `{"en": "...", "fr": "..."}` |
| `registration_flow_steps` | `description_i18n` | `{"en": "...", "fr": "..."}` |
| `registration_step_screens` | `title_i18n` | `{"en": "...", "fr": "..."}` |
| `registration_step_screens` | `subtitle_i18n` | `{"en": "...", "fr": "..."}` |
| `registration_jurisdictions` | `supported_languages` | `["en", "fr"]` |

### SQLAlchemy models updated

`database.py`: new columns added to `RegistrationFlowStep`, `RegistrationStepScreen`, and `RegistrationJurisdiction`.

### Pydantic schemas updated

`admin_router.py`: `StepCreate`/`StepUpdate` and `ScreenCreate`/`ScreenUpdate` now accept `title_i18n`, `subtitle_i18n`, `description_i18n` as `Optional[Dict[str, str]]`.

### Serialization updated

Admin serializers (`_ser_step`, `_ser_screen`, `_ser_jurisdiction`) now include i18n fields in responses.

---

## Runtime Language Resolution

### `i18n.py` helper module

New file `api/services/registration/i18n.py` with two functions:

- `resolve_localized(value, lang, default_lang)` — handles `str`, `dict`, `None`
- `resolve_localized_props(props, lang, default_lang)` — resolves `label`, `placeholder`, `text`, `content`, `items`, `options.label`

### Fallback chain

`requested lang → default_lang → "en" → first available → ""`

### `?lang=` query parameter

`GET /api/registration/flows/active?jurisdiction=EU&lang=fr`

When `lang` is provided:
1. Step `title`/`description` resolved from `title_i18n`/`description_i18n`
2. Screen `title`/`subtitle` resolved from `title_i18n`/`subtitle_i18n`
3. Component `props` resolved via `resolve_localized_props()`

When `lang` is absent: falls back to jurisdiction `default_language`.

### Backward compatibility

- If `title_i18n` is `null`, `title` (plain text) is used
- If `props.label` is a string, it passes through unchanged
- No migration of existing data required

---

## Admin Builder Enhancements

### i18n editing

Each editable entity now has language tabs (en/fr):

- **Steps**: Title i18n + Description i18n
- **Screens**: Title i18n + Subtitle i18n
- **Components**: Label i18n + Placeholder i18n + Text i18n

The `I18nField` component renders side-by-side inputs for each language.

The `cleanI18n()` helper strips empty values before saving, sending `null` if all languages are empty.

### Component form adaptation

The form dynamically shows/hides fields based on `component_type`:
- `divider` and `spacer`: no label
- Content types: no binding_slug, no required, no placeholder
- `select`/`multi_select`: options JSON textarea
- `legal_content`/`info_box`/`rich_text`: text textarea with i18n
- `bullet_list`: items JSON textarea
- `spacer`: height number input

---

## Flutter/Web Renderer Support

### Flutter — 4 new components

Added in `registration_flow_renderer.dart`:

| Type | Widget | Notes |
|------|--------|-------|
| `rich_text` | `Text` with secondary color | Whitespace-preserving paragraph |
| `divider` | `Divider` | 1px with subtle color |
| `spacer` | `SizedBox` | Height from `props.height` (default 16) |
| `bullet_list` | `Column` with bullet points | Label + items list with `•` prefix |

### Flutter — i18n transparency

Flutter does not need i18n changes. The backend resolves localized values before sending the response. Flutter receives plain strings in `props.label`, `props.text`, etc., regardless of whether the source was a plain string or a localized JSON object.

### Web preview — all 14 types

`ComponentPreview` in the preview page now handles all 14 component types with no "Unknown" fallback for any supported type.

---

## Tests Added

### Backend (21 tests)

`api/tests/test_registration_i18n.py`:

- `TestResolveLocalized` (9 tests): plain string, None, dict exact/fallback/chain, empty dict, coercion, backward compat
- `TestResolveLocalizedProps` (9 tests): plain props, localized label/text/options/items, empty, fallback, non-localizable preserved
- `TestComponentTypes` (3 tests): 14 types categorized, content vs input classification

### Flutter (4 new tests)

`mobile/test/registration/registration_renderer_test.dart`:

- `rich_text` renders as paragraph text
- `divider` renders as Divider widget
- `spacer` renders as SizedBox with correct height
- `bullet_list` renders label + all items

---

## Backward Compatibility Notes

| Aspect | Compatibility |
|--------|--------------|
| Existing plain-string `title`/`subtitle` | ✅ Unchanged — used when i18n columns are null |
| Existing `props_json` with string values | ✅ `resolve_localized()` passes strings through |
| Existing Flutter renderer | ✅ Unknown types still render as `SizedBox.shrink()` |
| Existing seed data | ✅ No migration of seed data required |
| Existing sessions | ✅ Session service uses same fallback logic |
| Runtime API without `?lang=` | ✅ Uses jurisdiction `default_language` |
| Admin API without i18n fields | ✅ New fields are `Optional`, not required |

---

## Remaining Gaps / Next Steps

| Gap | Priority | Effort |
|-----|----------|--------|
| Drag-and-drop reorder (currently ▲▼ buttons) | Low | Medium |
| Visibility rule editor (currently JSON only in backend) | Medium | Medium |
| Validation rule editor | Medium | Medium |
| Field definitions catalog browser in admin | Low | Medium |
| Flow publish/archive buttons in admin | Medium | Small |
| `layout_type` branching in Flutter | Low | Small |
| `config_json` parsing in Flutter | Low | Small |
| Translation completeness warnings in admin | Low | Small |
| `supported_languages` management UI | Low | Small |
| Rich text markdown/HTML rendering in Flutter | Low | Medium |
