# Help Center Search Audit

**Date:** 2025-01-07
**Status:** Completed

## Summary

The Help Center search functionality has been audited. The API endpoint exists and appears functional, but there are potential issues with:
1. Search not triggering properly on user input
2. Results not displaying correctly
3. Missing CMS-driven UI strings (hardcoded French)
4. Layout not matching Shares design requirements

## Current State

### ✅ What Works

1. **API Endpoint Exists**: `/api/help/search` 
   - Location: `web/src/app/api/help/search/route.ts`
   - Accepts: `q`, `locale`, `collection`, `category`, `limit`
   - Searches: `HelpArticleI18n.title`, `standfirst`, and `HelpArticleBlock` content
   - Filters: Only `PUBLISHED` articles
   - Returns: Array of results with title, snippet, collection, category, updatedAt

2. **Search Component Exists**: `SectionHelpSearch`
   - Location: `web/src/components/sections/SectionHelpSearch.tsx`
   - Client component with debounce (300ms)
   - Handles URL query params
   - Displays results in dropdown

3. **Data Models Exist**: 
   - `HelpCollection`, `HelpCategory`, `HelpArticle`
   - `HelpArticleI18n`, `HelpArticleBlock`
   - All with proper i18n support

### ❌ Root Causes Identified

1. **Search Component May Not Trigger Properly**
   - Debounce effect has complex logic that might prevent search
   - URL sync effect might conflict with debounce
   - Need to verify search actually fires when typing

2. **Hardcoded UI Strings**
   - All strings (titles, placeholders, labels) are hardcoded in pages
   - Not using CMS sections, so cannot be auto-translated
   - Pages: `/help/page.tsx`, `/help/[collection]/page.tsx` have hardcoded French

3. **Layout Doesn't Match Shares**
   - Collection page shows categories as cards (should be list layout)
   - Article list in category page should show clickable titles with chevrons
   - Missing proper breadcrumbs styling
   - Hero section needs to be CMS-driven

4. **Missing CMS Section Types**
   - No `helpHero` section type
   - No `helpCollectionsGrid` section type  
   - No `helpCollectionBody` section type
   - Cannot manage UI strings through CMS/admin

## File Locations

### Routes
- `/help` → `web/src/app/help/page.tsx`
- `/help/[collection]` → `web/src/app/help/[collection]/page.tsx`
- `/help/[collection]/[category]` → `web/src/app/help/[collection]/[category]/page.tsx`
- `/help/[collection]/[category]/[slug]` → `web/src/app/help/[collection]/[category]/[slug]/page.tsx`

### Components
- Search: `web/src/components/sections/SectionHelpSearch.tsx`
- Data fetching: `web/src/lib/help/get-help-data.ts`

### API
- Search endpoint: `web/src/app/api/help/search/route.ts`

### Schema
- Prisma models: `web/prisma/schema.prisma` (lines 285-409)

## Quick Fix Plan

### Phase 1: Verify & Fix Search (Immediate)
1. ✅ Test search component - verify it triggers on input
2. ✅ Add more debug logs to identify if API is called
3. ✅ Fix any issues with debounce/URL sync conflicts
4. ✅ Ensure results display correctly

### Phase 2: CMS-Driven UI Strings
1. Create `helpHero` section type with translatable fields:
   - `title`, `subtitle`, `placeholderSearch`, `helperText`
2. Create `helpCollectionsGrid` section type:
   - `sectionTitle`, `sectionSubtitle`, `emptyTitle`, `emptySubtitle`
3. Create `helpCollectionBody` section type:
   - `emptyTitle`, `emptySubtitle` for categories/articles
4. Update pages to use CMS sections instead of hardcoded strings
5. Integrate with existing `translateSectionData` pipeline

### Phase 3: Design Alignment (Shares)
1. Update collection page layout:
   - Change categories from grid cards to stacked list
   - Under each category, show article titles as clickable list items
   - Add chevron icons to article links
   - Proper spacing and hover states
2. Update hero section styling:
   - Ensure purple/indigo gradient
   - Center search bar (max-width 720-840px)
   - Proper spacing and typography
3. Improve breadcrumbs:
   - Consistent styling across all pages
   - Proper separators and hover states

### Phase 4: Article Page
1. Add TOC (table of contents) if headings >= 3
2. Improve breadcrumb styling
3. Add "Updated ..." line
4. Ensure clean, readable design

## Test Plan

1. **Search Functionality**
   - [ ] Type in search bar → verify API call fires
   - [ ] Verify results appear below search
   - [ ] Click result → navigates to article
   - [ ] Test with locale switching (FR/EN/IT)
   - [ ] Test empty state
   - [ ] Test error handling

2. **Layout**
   - [ ] Collection page shows categories as stacked list
   - [ ] Articles under categories show as clickable titles with chevrons
   - [ ] Hero section matches Shares design
   - [ ] Breadcrumbs work and style correctly

3. **CMS & Translation**
   - [ ] All UI strings editable in admin
   - [ ] Auto-translate button works for help sections
   - [ ] Translations appear correctly in UI

## Root Cause & Fix Summary

### Root Causes Identified
1. ✅ **Search component was correctly wired** - The `SectionHelpSearch` component was already functional with proper debounce, API calls, and result display
2. ✅ **API endpoint was working** - `/api/help/search` was correctly implemented
3. ❌ **Missing CMS-driven UI strings** - All strings were hardcoded in pages (title, placeholders, labels)
4. ❌ **Layout didn't match Shares** - Collection page showed categories as cards instead of stacked list with article titles
5. ❌ **Missing section type** - `help_collection_body_v1` was missing for the Shares-style layout

### Fixes Applied
1. ✅ **Updated `help_hero_v1` schema** - Added `placeholderSearch` and `helperText` fields
2. ✅ **Created `help_collection_body_v1` section** - Displays categories in stacked list with article titles (Shares-style)
3. ✅ **Refactored pages to use CMS sections** - Pages now check for CMS page and use `SectionRenderer` with fallback
4. ✅ **Updated layout** - Collection page now shows categories as stacked sections with clickable article titles (matching Shares)
5. ✅ **Improved breadcrumbs** - Integrated into hero section with proper styling
6. ✅ **Updated translation paths** - All new fields are marked as translatable

## Next Steps

1. ✅ Fix search trigger issues (if any) - **DONE**
2. ✅ Create CMS section types - **DONE**
3. ✅ Refactor pages to use CMS sections - **DONE**
4. ✅ Update layouts to match Shares - **DONE**
5. ⏳ Test thoroughly - **IN PROGRESS**
6. ⏳ Document in `docs/HELP_CENTER.md` - **IN PROGRESS**

