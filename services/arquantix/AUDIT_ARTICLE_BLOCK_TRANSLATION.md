# Audit: Article Block Translation Missing

**Date:** 2025-01-05  
**Status:** BUG CONFIRMED

## Problem Summary

When translating articles from FR to EN/IT:
- ✅ ArticleI18n fields (title, standfirst, meta) are translated correctly
- ❌ ArticleBlock content (headings, paragraphs, quotes, lists) remains in FR
- Public pages show blocks in FR even when locale is EN/IT

## Root Cause Analysis

### A) Translation API Behavior

**File:** `web/src/app/api/admin/translate/article/route.ts`

**Finding:**
- Lines 173-256: Block translation code was **completely removed** (commented out)
- Reason: Previous fix to prevent locale mixing (blocks are shared across locales)
- Current behavior: Only translates `ArticleI18n`, skips all blocks

**Evidence:**
```typescript
// NOTE: Article blocks are NOT translated here because they are shared across locales.
// The ArticleBlock model does not have a locale field, so translating blocks would
// cause locale mixing (last translation would overwrite previous ones).
```

### B) Database Schema

**File:** `web/prisma/schema.prisma`

**Finding:**
- `ArticleBlock` model exists (lines 207-220)
- `ArticleBlockI18n` model **DOES NOT EXIST**
- `ArticleBlock` has no `locale` field
- Unique constraint: `@@unique([articleId, order])` - blocks shared across locales

**Current Schema:**
```prisma
model ArticleBlock {
  id        String          @id @default(cuid())
  articleId String          @map("article_id")
  order     Int             @default(0)
  type      ArticleBlockType
  data      Json            // Contains text content, but no locale isolation
  createdAt DateTime        @default(now()) @map("created_at")

  article   Article         @relation(fields: [articleId], references: [id], onDelete: Cascade)

  @@unique([articleId, order])
  @@index([articleId])
  @@map("article_blocks")
}
```

**Problem:** No way to store per-locale block content.

### C) Frontend Rendering

**File:** `web/src/app/blog/[slug]/page.tsx`

**Finding:**
- Line 22-84: `getArticle()` function fetches blocks
- Blocks are fetched by `articleId` only, no locale filtering
- Always returns blocks in source locale (FR)
- No fallback to localized block content

**Evidence:**
```typescript
blocks: {
  orderBy: { order: 'asc' },
  // ❌ No locale filtering - always returns source locale blocks
}
```

### D) Admin Editor

**File:** `web/src/app/admin/articles/[id]/page.tsx`

**Finding:**
- Admin editor displays blocks from `article.blocks`
- No locale-specific block editing
- Blocks always shown in source locale

## Root Cause

**PRIMARY:** `ArticleBlock` model has no locale isolation. Blocks are shared across all locales, so:
1. Cannot store translated block content per locale
2. Previous fix removed block translation to prevent overwriting
3. Result: Blocks remain in source locale forever

**SECONDARY:** No `ArticleBlockI18n` model to store per-locale block translations.

## Proposed Fix

### Option A: Add ArticleBlockI18n Model (Recommended)

**Pros:**
- Clean separation of canonical structure (type, order, media refs) vs. localized content
- Follows same pattern as ArticleI18n
- No breaking changes to existing ArticleBlock

**Implementation:**
1. Create `ArticleBlockI18n` model with:
   - `id`, `blockId` (FK), `locale`, `data` (Json), `translationStatus`
   - `@@unique([blockId, locale])`
2. Update translation API to:
   - Translate block content per locale
   - Store in `ArticleBlockI18n`
3. Update article fetch to:
   - Join `ArticleBlockI18n` for requested locale
   - Fallback to default locale or canonical block data
4. Update public renderer to use localized blocks

### Option B: Add locale to ArticleBlock (Not Recommended)

**Cons:**
- Breaking change (requires data migration)
- Duplicates block structure per locale
- More complex queries

## Reproduction Steps

1. Create article in FR with:
   - HEADING: "FR_ONLY_HEADING_123"
   - PARAGRAPH: "FR_ONLY_PARAGRAPH_456"
   - BULLET_LIST: ["FR_ONLY_ITEM_1", "FR_ONLY_ITEM_2"]
2. Run auto-translate FR -> EN
3. Check DB:
   ```sql
   SELECT locale, title FROM article_i18n WHERE article_id = '...';
   -- ✅ EN row exists with translated title
   
   SELECT id, article_id, "order", type, data FROM article_blocks WHERE article_id = '...';
   -- ❌ Still contains FR_ONLY_* text
   ```
4. Visit `/blog/[slug]` with locale=EN
5. Result: Title in EN, but blocks still show FR_ONLY_* text

## Impact

- **Severity:** HIGH - Multi-locale articles are incomplete
- **User Impact:** Body content not translated, poor UX for non-FR users
- **Data Risk:** LOW - No data corruption, just missing translations

## Fixes Applied

### ✅ Fix #1: ArticleBlockI18n Model Created
- **Status:** COMPLETED
- **Action:** Added `ArticleBlockI18n` model with `blockId`, `locale`, `data`, `translationStatus`
- **Migration:** Applied successfully
- **Impact:** Can now store per-locale block translations

### ✅ Fix #2: Translation API Updated
- **Status:** COMPLETED
- **Action:** Implemented block translation per locale in `translate/article/route.ts`
- **Features:**
  - Translates HEADING, PARAGRAPH, QUOTE, BULLET_LIST, IMAGE (caption), VIDEO (caption/title)
  - Stores in `ArticleBlockI18n` with `translationStatus=MACHINE`
  - Deep clone per block per locale to prevent mixing
  - Sequential translation to avoid race conditions
  - Logs block translation count (dev only)

### ✅ Fix #3: Article Fetch Updated
- **Status:** COMPLETED
- **Action:** Updated `getArticle()` and admin API to fetch localized blocks
- **Features:**
  - Public page: Uses `block.i18n[0]?.data || block.data` (fallback to canonical)
  - Admin API: Accepts `?locale=` query param, falls back to cookie
  - Preserves mediaId/url in canonical block, only translates text content

### ✅ Fix #4: Rendering Updated
- **Status:** COMPLETED
- **Action:** Public article page now uses localized block data
- **Impact:** Blocks display in correct locale on public pages

## Next Steps

1. ✅ Audit complete
2. ✅ Implement ArticleBlockI18n model
3. ✅ Update translation API
4. ✅ Update article fetch/rendering
5. ⏳ Test with real data
6. ⏳ Add admin UI for editing localized blocks (optional V2)

