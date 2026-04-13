# Audit: Auto-translate Locale Mixing Bug

**Date:** 2025-01-05  
**Status:** CRITICAL BUG FOUND

## Problem Summary

When translating content from FR to EN + IT, translations end up "mixed":
- FR content contains Italian fragments
- EN content contains FR/IT fragments
- IT content may contain EN fragments

## Root Causes Identified

### 🔴 CRITICAL BUG #1: Article Blocks Shared Across Locales

**Location:** `web/src/app/api/admin/translate/article/route.ts` (lines 174-256)

**Problem:**
- `ArticleBlock` model does NOT have a `locale` field
- All locales share the same blocks (same `articleId` + `order`)
- When translating to EN, blocks are updated with EN content
- When translating to IT next, the SAME blocks are updated with IT content, **overwriting EN**
- Result: Only the last translated locale's content remains in blocks

**Evidence:**
```typescript
// Line 252-255: Updates the SAME block for ALL locales
await prisma.articleBlock.update({
  where: { id: sourceBlock.id },  // ❌ Same block ID for all locales!
  data: { data: translatedData },
})
```

**Impact:** Article blocks are completely broken for multi-locale content.

### 🟡 POTENTIAL BUG #2: Deep Clone in translateSectionData

**Location:** `web/src/lib/translate/translateSectionData.ts` (line 99)

**Current Implementation:**
```typescript
const translated = JSON.parse(JSON.stringify(data))
```

**Potential Issues:**
- JSON.parse/stringify can fail on circular references
- May lose special object types (Date, RegExp, etc.)
- However, for simple JSON data structures, this should work

**Status:** Likely OK for current use case, but should use `structuredClone()` if available (Node 18+)

### ✅ VERIFIED CORRECT: Upsert Keys

**Location:** All translate routes

**Verification:**
- `SectionContent`: Uses `sectionId_locale_status` unique constraint ✅
- `ProjectI18n`: Uses `projectId_locale` unique constraint ✅
- `ArticleI18n`: Uses `articleId_locale` unique constraint ✅

**Status:** Upsert keys are correct and include locale.

### ✅ VERIFIED CORRECT: Sequential Translation

**Location:** All translate routes

**Verification:**
- All routes use `for (const targetLocale of targetLocales)` with `await` inside
- Translations are sequential, not parallel
- Each locale has its own scope

**Status:** No race conditions in translation loops.

## Reproduction Steps

1. Create an article in FR with blocks:
   - Heading: "FR_ONLY_ABC123"
   - Paragraph: "FR_ONLY_XYZ789"
2. Run auto-translate to EN + IT
3. Check database:
   ```sql
   SELECT locale, title, standfirst FROM article_i18n WHERE article_id = '...';
   -- Should show separate rows for fr, en, it ✅
   
   SELECT id, article_id, "order", type, data FROM article_blocks WHERE article_id = '...';
   -- Will show SAME blocks for all locales ❌
   ```
4. Result: Only the last translated locale's content remains in blocks

## Fixes Required

### Fix #1: Article Blocks Locale Isolation (CRITICAL)

**Option A: Add locale field to ArticleBlock (Recommended)**
- Requires Prisma migration
- Each locale gets its own blocks
- Clean separation

**Option B: Store translated blocks in ArticleI18n.data (Quick Fix)**
- No schema change
- Blocks remain shared, but translations stored in i18n
- Less clean but works immediately

**Option C: Skip block translation for now**
- Document limitation
- Only translate i18n fields (title, standfirst, meta)
- Blocks remain in source locale

### Fix #2: Improve Deep Clone (Optional)

Replace `JSON.parse(JSON.stringify())` with `structuredClone()` if Node 18+:
```typescript
const translated = structuredClone(data)
```

### Fix #3: Add Validation & Logging

- Log each translation with locale, entityId, preview of output
- Add sanity check: verify output doesn't contain source locale sentinel tokens
- Add guardrails to prevent translating to same locale as source

## Test Plan

1. Create test article with sentinel tokens in FR
2. Translate to EN + IT
3. Verify:
   - FR i18n unchanged
   - EN i18n contains only English (no FR/IT sentinels)
   - IT i18n contains only Italian (no FR/EN sentinels)
   - Blocks: TBD based on fix chosen

## Risk Assessment

- **Data Loss Risk:** HIGH - Current article block translations are corrupted
- **Fix Complexity:** MEDIUM - Requires schema change or architectural decision
- **Backward Compatibility:** LOW - Existing multi-locale articles may need re-translation

## Fixes Applied

### ✅ Fix #1: Article Blocks Translation Removed
- **Status:** COMPLETED
- **Action:** Removed block translation code that was causing locale mixing
- **Impact:** Article blocks now remain in source locale (no mixing)
- **Note:** Future enhancement: Add locale field to ArticleBlock schema for true multi-locale support

### ✅ Fix #2: Deep Clone Improvement
- **Status:** COMPLETED
- **Action:** Updated `translateSectionData` to use `structuredClone()` when available
- **Impact:** Better isolation, handles edge cases better

### ✅ Fix #3: Logging & Validation Added
- **Status:** COMPLETED
- **Action:** Added dev-only logging and verification after DB writes
- **Impact:** Can now detect locale mismatches during development

### ✅ Fix #4: Input Validation Enhanced
- **Status:** COMPLETED
- **Action:** Added validation to prevent sourceLocale in targetLocales and duplicate targets
- **Impact:** Prevents invalid translation requests at API level

## Summary

**Root Cause:** ArticleBlocks were being translated and updated in-place, causing the last translated locale to overwrite previous translations since blocks are shared across locales.

**Solution:** Removed block translation entirely. Blocks now remain in source locale. Only i18n fields (title, standfirst, meta) are translated per locale.

**Status:** ✅ FIXED - Locale mixing prevented for i18n fields. Article blocks limitation documented.

## Next Steps

1. ✅ Audit complete
2. ✅ Implement Fix #1 (removed block translation)
3. ✅ Add logging/instrumentation
4. ✅ Add input validation
5. ⏳ Test with real data
6. ⏳ Document limitations (blocks remain in source locale) - DONE in code comments

## Known Limitations

- **Article Blocks:** Blocks are NOT translated per locale. They remain in the source locale. To support multi-locale blocks, the schema would need to be updated to add a `locale` field to `ArticleBlock`.
- **Section/Project/Article i18n:** ✅ Fully isolated per locale (no mixing)

