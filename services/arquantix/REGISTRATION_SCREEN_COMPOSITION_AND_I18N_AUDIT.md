# Registration Screen Composition & i18n Audit

## Executive Summary

The registration builder is a **functional but under-leveraged** system. The data model already supports full screen composition (title, subtitle, content components, input components, legal blocks) — the limiting factor is the admin UI which only exposes a subset of backend capabilities, and the absence of any i18n mechanism.

**Key findings:**

1. **Screen composition is already possible** — screens carry `title`, `subtitle`, `config_json`; components support `section_title`, `legal_content`, and `info_box` alongside input types. A complete screen with title + description + fields + legal footer can be built **today** without schema changes.

2. **The admin builder is the bottleneck** — the backend API supports reordering, visibility rules, validation rules, field definition catalog, publish/archive lifecycle — none of which the admin edit page exposes.

3. **i18n does not exist** — all text is stored as plain strings. No localized JSON, no translation keys, no per-language variants. `default_language` exists on jurisdiction but serves no translation purpose.

4. **Flutter renderer is solid** — it handles 10 component types including non-input types (`section_title`, `legal_content`, `info_box`). Unknown types are silently hidden. Adding new types requires only a new `case` in the switch.

5. **No schema migration needed** for basic screen composition — only admin UI improvements and i18n column additions.

---

## Current Admin Builder Capabilities

### What the builder CAN do today

| Capability | How | Where |
|-----------|-----|-------|
| Create/edit/delete steps | Full CRUD | Edit page, column 1 |
| Set step title + description | Text fields | Step edit form |
| Set step as blocking/optional | Boolean toggles | Step edit form |
| Reorder steps | Dedicated API endpoint | `POST .../steps/reorder` (backend only — **not wired in UI**) |
| Create/edit/delete screens | Full CRUD | Edit page, column 2 |
| Set screen title + subtitle | Text fields | Screen edit form |
| Set screen layout_type | Dropdown: `form`, `info`, `document` | Screen edit form |
| Create/edit/delete components | Full CRUD | Edit page, column 3 |
| Set component type | Dropdown of 9 types | Component create form |
| Set label, required, placeholder | Text/boolean fields | Component edit form |
| Set select options | JSON string input | Component edit form (select/multi_select) |
| Bind to field_definition | Via `binding_slug` | Component edit form |

**9 component types in the admin UI:**
`text_input`, `phone_input`, `select`, `country_picker`, `date_picker`, `checkbox`, `multi_select`, `section_title`, `legal_content`

### What the builder CANNOT do today

| Gap | Detail | Backend support? |
|-----|--------|-----------------|
| Reorder screens | No drag & drop or reorder UI | YES — `POST .../screens/reorder` exists |
| Reorder components | No drag & drop or reorder UI | YES — `POST .../components/reorder` exists |
| Edit `config_json` on screen | Not exposed in UI | YES — `PATCH .../screens/{id}` accepts it |
| Edit visibility rules | Not exposed in UI | YES — `visibility_rule_json` on steps/components |
| Edit validation rules | Not exposed in UI | YES — `validation_rule_json` on components |
| Edit completion rules | Not exposed in UI | YES — `completion_rule_json` on steps |
| Browse field definitions catalog | Not exposed in UI | YES — `GET /field-definitions/catalog` |
| Publish/archive flows | Not exposed in UI | YES — `POST .../publish`, `.../archive` |
| Preview `multi_select` | Falls through to "Unknown" in preview | Stored correctly, not rendered |
| Add rich text / info_box / divider | No UI for these types | `component_type` is free text — can be added |
| Localize any text | No i18n UI | No backend support either |
| Sidebar link | Not in `AdminSidebar.tsx` | Access via direct URL only |

---

## Data Model Audit

### Hierarchy

```
RegistrationJurisdiction (EU, UAE, ...)
  └── RegistrationFlow (draft/active/archived, versioned)
        └── RegistrationFlowStep (ordered by position)
              └── RegistrationStepScreen (ordered by position)
                    └── RegistrationScreenComponent (ordered by position)
```

### Screen columns

| Column | Type | Nullable | Purpose |
|--------|------|----------|---------|
| `id` | UUID | No | PK |
| `step_id` | UUID FK | No | Parent step |
| `screen_key` | Text | No | Unique within step |
| `title` | Text | No | **Already supports configurable page title** |
| `subtitle` | Text | Yes | **Already supports configurable page subtitle** |
| `position` | Integer | No | Ordering |
| `layout_type` | Text | No | `form` / `info` / `document` (default: `form`) |
| `config_json` | JSONB | Yes | **Free-form metadata — can carry any structured config** |

**Verdict:** Screen-level title/subtitle are **already modeled**. `config_json` can carry additional metadata (header image, theme, background, etc.) without schema change.

### Component columns

| Column | Type | Nullable | Purpose |
|--------|------|----------|---------|
| `id` | UUID | No | PK |
| `screen_id` | UUID FK | No | Parent screen |
| `component_type` | Text | No | **Free-form string — not an enum** |
| `component_key` | Text | No | Unique within screen |
| `position` | Integer | No | Ordering |
| `props_json` | JSONB | Yes | All component configuration |
| `binding_slug` | Text | Yes | Links to field_definition for data collection |
| `field_definition_id` | UUID FK | Yes | Optional link to catalog |
| `visibility_rule_json` | JSONB | Yes | Conditional display rules |
| `validation_rule_json` | JSONB | Yes | Input validation rules |

**Verdict:** Components can carry **any type** since `component_type` is free text. `props_json` is the universal configuration bag. Non-input types (titles, text blocks, legal, dividers) work naturally — they simply have no `binding_slug`.

### Can a legal footer be modeled without hack?

**YES.** It's a component with:
```json
{
  "component_type": "legal_content",
  "component_key": "terms_footer",
  "position": 99,
  "props_json": {
    "label": "Terms Notice",
    "text": "By continuing, you agree to our Terms and Privacy Policy."
  },
  "binding_slug": null
}
```

This already exists in the seed data (migration 087).

### Can editorial/marketing content be modeled?

**YES** — via `section_title` (for headings) and `legal_content` or `info_box` (for body text). But there is no `rich_text` component for formatted content, and no `bullet_list`, `divider`, or `spacer` types.

### i18n in the data model

**Does not exist.** All text columns are plain strings:
- `step.title`, `step.description` — plain text
- `screen.title`, `screen.subtitle` — plain text
- `component.props_json.label`, `.placeholder`, `.text` — plain text
- `field_definitions.field_name_en` — English label (name implies single language)
- `jurisdiction.default_language` — metadata only, no translation lookup

---

## Runtime Audit (Flutter + Web)

### Flutter component dispatch

The renderer in `registration_flow_renderer.dart` uses a `switch` on `comp.componentType`:

| `component_type` | Widget rendered | Category |
|-------------------|----------------|----------|
| `text_input` | `TextField` (email/number/phone keyboard variants) | Input |
| `phone_input` | `TextField` (phone keyboard) | Input |
| `select` | `DropdownButtonFormField` | Input |
| `multi_select` | Custom checkbox group | Input |
| `country_picker` | `DropdownButtonFormField` with country list | Input |
| `date_picker` | `TextField` + `showDatePicker` | Input |
| `checkbox` | `CheckboxListTile` | Input |
| `section_title` | `Text` (bold, `comp.label`) | Content |
| `legal_content` | `Text` (`props['text']` or `props['content']`) | Content |
| `info_box` | `Container` with info styling + `Text` | Content |
| `default` | `SizedBox.shrink()` (invisible) | Fallback |

**Screen metadata usage:**
- `screen.title` → displayed as heading in scroll body (if non-empty)
- `screen.subtitle` → displayed below title in body
- AppBar title → `currentStep.title` (step level, not screen level)
- `layout_type` → stored in model but **not used for UI branching**
- `config_json` → **not parsed by Flutter** (the `config` field from API is ignored)

### Can we build a complete registration screen today?

**Question:** Can we compose a screen with title + description + fields + legal footer?

| Element | Supported? | How |
|---------|-----------|-----|
| Page title | YES | `screen.title` (displayed in body) |
| Page subtitle/description | YES | `screen.subtitle` (displayed in body) |
| Section heading | YES | `section_title` component |
| Text input fields | YES | `text_input`, `phone_input`, etc. |
| Select / pickers | YES | `select`, `country_picker`, `date_picker` |
| Checkboxes | YES | `checkbox` |
| Info box | YES | `info_box` component |
| Legal footer | YES | `legal_content` component (last position) |
| Rich formatted text | NO | No `rich_text` component type |
| Bullet list | NO | No `bullet_list` component type |
| Divider / spacer | NO | No `divider` / `spacer` component type |

**Answer: YES — a complete functional screen is possible today**, with the limitation that text content is plain (no markdown/HTML formatting) and there are no visual layout components (dividers, spacers).

### Web admin preview

The preview page (`flows/[id]/preview/page.tsx`) renders `ComponentPreview` with similar type dispatch. It supports: `text_input`, `phone_input`, `country_picker`, `date_picker`, `checkbox`, `select`, `legal_content`, `section_title`. **`multi_select` falls through to "Unknown component type"** in preview.

---

## i18n Audit

### Current state

| Layer | Localization support | Detail |
|-------|---------------------|--------|
| Database columns | NONE | All text in `title`, `subtitle`, `description`, `props_json.label` is plain string |
| Backend API | NONE | No language parameter, no translation lookup |
| Admin builder | NONE | No language selector, no side-by-side translation |
| Flutter runtime | NONE | Strings from API displayed as-is |
| Seed data | English only | Seeds use English text (migration 085, 087) |
| Jurisdiction | `default_language` column exists | Metadata only — no dispatch to translations |

### Recommendation: Localized JSON vs i18n Keys

**Option A — i18n keys** (e.g., `"label": "reg.personal.first_name"`)
- Pros: Clean separation, standard, works with existing i18n frameworks (intl, arb)
- Cons: Requires a translation management system, key registry, build-time or runtime lookup, more complex admin UI (key picker + preview), breaks the "what you see is what you configure" admin experience

**Option B — Localized JSON** (e.g., `"label": {"fr": "Prénom", "en": "First Name"}`)
- Pros: Self-contained (no external system), admin can edit all languages inline, runtime picks language from context, progressive (start with 1 language, add others), works with existing JSONB storage
- Cons: Larger payloads, duplicated text management, harder to enforce completeness

### Recommendation: **Option B — Localized JSON**

Rationale:
1. **Pragmatic** — `props_json` is already JSONB; changing `"label": "First Name"` to `"label": {"en": "First Name", "fr": "Prénom"}` is backward-compatible
2. **Admin-friendly** — the builder can show tabs per language without needing a key registry
3. **Runtime-simple** — Flutter picks `props['label'][lang]` with fallback to `'en'`
4. **No external dependency** — no translation management platform needed
5. **Matches jurisdiction model** — `default_language` already exists; extend to `supported_languages` array

For screen-level text (`title`, `subtitle`), two sub-options:
- **A) Add `title_i18n` / `subtitle_i18n` JSONB columns** alongside existing text columns (backward-compatible)
- **B) Use `config_json`** to carry localized variants (no migration needed but less explicit)

**Recommended: Option A (new JSONB columns)** for explicit semantics and query support.

---

## Current Component Catalog

### A. Screen-level metadata (NOT components)

| Field | Exists? | Stored where | Rendered? |
|-------|---------|-------------|-----------|
| Page title | YES | `screen.title` | YES (Flutter body, admin preview) |
| Page subtitle | YES | `screen.subtitle` | YES (Flutter body, admin preview) |
| Layout type | YES | `screen.layout_type` | NO (stored but unused in Flutter) |
| Screen config | YES | `screen.config_json` | NO (not parsed by Flutter) |

### B. Content/layout components

| Type | Exists? | In admin builder? | In Flutter? | In seeds? |
|------|---------|-------------------|-------------|-----------|
| `section_title` | YES | YES | YES | YES (085) |
| `legal_content` | YES | YES | YES | YES (085, 087) |
| `info_box` | YES | NO | YES | NO |
| `rich_text` | NO | — | — | — |
| `divider` | NO | — | — | — |
| `spacer` | NO | — | — | — |
| `bullet_list` | NO | — | — | — |
| `image` | NO | — | — | — |

### C. Input components

| Type | Exists? | In admin builder? | In Flutter? | In seeds? | Validation? |
|------|---------|-------------------|-------------|-----------|-------------|
| `text_input` | YES | YES | YES | YES | YES (email, required) |
| `phone_input` | YES | YES | YES | YES | YES (phone format) |
| `select` | YES | YES | YES | YES | YES (options match) |
| `multi_select` | YES | YES | YES (renderer) | YES | YES (options match) |
| `country_picker` | YES | YES | YES | YES | NO (no validator) |
| `date_picker` | YES | YES | YES | YES | YES (date format) |
| `checkbox` | YES | YES | YES | YES | YES (boolean) |

### What should be components vs screen metadata?

| Element | Recommendation | Rationale |
|---------|---------------|-----------|
| Page title | **Screen metadata** (`screen.title`) | Already exists, always shown first, not reorderable |
| Page subtitle | **Screen metadata** (`screen.subtitle`) | Already exists, always shown second |
| Section heading | **Component** (`section_title`) | Can appear anywhere in the component list |
| Body text | **Component** (new `rich_text`) | Reorderable, can appear between fields |
| Info callout | **Component** (`info_box`) | Already exists in Flutter |
| Legal footer | **Component** (`legal_content`) | Already exists, placed last by position |
| Divider | **Component** (new `divider`) | Simple visual separator between components |
| Spacer | **Component** (new `spacer`) | Vertical whitespace |
| Bullet list | **Component** (new `bullet_list`) | Structured list content |

---

## Missing Capabilities

### Priority 1 — Must have for configurable screens

| Gap | Impact | Effort |
|-----|--------|--------|
| Admin: reorder components (drag & drop) | Cannot control layout order | Medium (backend ready, UI work) |
| Admin: reorder screens | Cannot control screen order | Medium (backend ready, UI work) |
| Admin: expose `info_box` in component types | Flutter supports it but admin doesn't offer it | Trivial (add to `COMPONENT_TYPES` list) |
| Admin: sidebar link to Registration | Accessible only via URL | Trivial |
| i18n on props_json (label, placeholder, text) | Cannot translate | Medium (convention + admin tabs) |
| i18n on screen title/subtitle | Cannot translate | Small (new columns or convention) |

### Priority 2 — Nice to have for rich screens

| Gap | Impact | Effort |
|-----|--------|--------|
| `rich_text` component | Cannot add formatted paragraphs | Small (new case in Flutter + admin) |
| `divider` component | Cannot visually separate sections | Trivial |
| `spacer` component | Cannot add vertical whitespace | Trivial |
| `bullet_list` component | Cannot show structured lists | Small |
| Admin: preview `multi_select` | Shows "Unknown" in preview | Trivial fix |
| Admin: edit visibility/validation rules | Backend supports but UI doesn't expose | Medium |
| Admin: field definitions catalog browser | Backend has catalog endpoint | Medium |
| Flutter: use `layout_type` for UI branching | Stored but ignored | Small |
| Flutter: parse `config_json` | Stored but ignored | Small |

---

## Recommended Screen Composition Architecture

### Principle: Evolve, don't rewrite

The existing architecture is sound. The registration engine has clean separation:
- **Config time**: admin builder → database (steps/screens/components)
- **Runtime**: API serializes → Flutter renders

The main gaps are in the **admin UI** (underexposed features) and **i18n** (absent).

### Target architecture (on top of existing)

```
Screen (title_i18n, subtitle_i18n, layout_type, config_json)
  ├── section_title    (props_json.label → localized)
  ├── rich_text         [NEW] (props_json.content → localized, markdown)
  ├── info_box          (props_json.text → localized)
  ├── text_input        (props_json.label/placeholder → localized)
  ├── select            (props_json.label/options → localized)
  ├── divider           [NEW] (no props needed)
  ├── spacer            [NEW] (props_json.height optional)
  ├── bullet_list       [NEW] (props_json.items → localized)
  ├── checkbox          (props_json.label → localized)
  └── legal_content     (props_json.text → localized)
```

### i18n convention for `props_json`

**Before (current):**
```json
{
  "label": "First Name",
  "placeholder": "Enter your first name",
  "required": true
}
```

**After (localized):**
```json
{
  "label": { "en": "First Name", "fr": "Prénom" },
  "placeholder": { "en": "Enter your first name", "fr": "Entrez votre prénom" },
  "required": true
}
```

**Runtime resolution:**
```dart
String resolveLocalized(dynamic value, String lang) {
  if (value is String) return value;           // backward compat
  if (value is Map) return value[lang] ?? value['en'] ?? '';
  return '';
}
```

This preserves backward compatibility — existing plain-string props continue to work.

### Screen-level i18n

Add 2 nullable JSONB columns to `registration_step_screens`:
- `title_i18n` JSONB — `{"en": "Personal Info", "fr": "Infos personnelles"}`
- `subtitle_i18n` JSONB — same structure

Runtime: if `title_i18n` exists and contains current language, use it; otherwise fall back to `title`.

Similarly for steps: `title_i18n` and `description_i18n` on `registration_flow_steps`.

---

## Minimal Changes Recommended

### Phase A — Quick wins (no schema change)

1. Add `info_box` to `COMPONENT_TYPES` in admin edit page
2. Fix `multi_select` rendering in admin preview
3. Add Registration link to `AdminSidebar.tsx`
4. Add `rich_text`, `divider`, `spacer` to `COMPONENT_TYPES` in admin
5. Add matching `case` branches in Flutter renderer for new types
6. Wire component/screen reorder buttons in admin UI (API already exists)

### Phase B — i18n foundation (small schema change)

1. Add `title_i18n` / `subtitle_i18n` JSONB columns to `registration_step_screens`
2. Add `title_i18n` / `description_i18n` JSONB columns to `registration_flow_steps`
3. Adopt localized JSON convention in `props_json` (backward-compatible)
4. Add `supported_languages` array column to `registration_jurisdictions`
5. Update admin builder: language tabs for text fields
6. Update Flutter `resolveLocalized()` helper
7. Update API to accept `?lang=` query parameter (with fallback to jurisdiction default)

### Phase C — Admin builder enrichment

1. Drag-and-drop reorder for components and screens
2. Field definitions catalog browser in component creation
3. Visibility rule editor (JSON → visual)
4. Validation rule editor
5. Flow publish/archive buttons
6. Live preview panel (currently separate page)

---

## Risks / Constraints

| Risk | Severity | Mitigation |
|------|----------|------------|
| Localized JSON increases payload size | LOW | Only active languages transmitted; JSONB compression |
| Backward compatibility with existing plain-string props | MEDIUM | `resolveLocalized()` handles both String and Map — zero migration needed for existing data |
| Admin builder complexity with i18n tabs | MEDIUM | Start with 2 languages (en, fr); add language management later |
| Flutter renderer becomes large switch | LOW | Already 10 cases; new content types are simple widgets |
| `config_json` and `layout_type` are unused in Flutter | LOW | No urgency — can be activated incrementally |
| No translation completeness enforcement | MEDIUM | Admin can show warnings for missing translations; not blocking |
| Seed data is English-only | LOW | Seeds can be updated progressively; existing flows continue to work |
| `field_definition_id` not serialized to Flutter | LOW | Backend fix: add to `_serialize_component()` when needed |
