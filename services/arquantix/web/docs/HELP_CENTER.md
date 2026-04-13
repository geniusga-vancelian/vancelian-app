# Help Center Management Guide

## Overview

The Help Center is a CMS-driven knowledge base system that allows you to create, organize, and translate help articles. All UI strings are editable through the CMS and support automatic translation.

## Structure

### Content Hierarchy
```
HelpCollection
  └── HelpCategory
      └── HelpArticle
          └── HelpArticleBlock (localized)
```

### Routes
- `/help` - Collections landing page
- `/help/[collection]` - Categories and articles in a collection (Shares-style list)
- `/help/[collection]/[category]` - Articles in a category
- `/help/[collection]/[category]/[slug]` - Individual article

## Admin Interface

### Collections (`/admin/help/collections`)
- Create collections with title, description, slug
- Reorder collections
- Publish/unpublish collections
- View article and category counts
- Manage localized labels (title, subtitle, description)
- Auto-translate collections

### Categories (`/admin/help/categories`)
- Filter by collection
- Create categories with title, description, slug
- Reorder categories within a collection
- Publish/unpublish categories
- Manage localized labels
- Auto-translate categories

### Articles (`/admin/help/articles`)
- Filter by collection, category, status, locale
- Search articles
- Create articles with title, slug, status
- Edit article content:
  - Settings: slug, status, publishedAt, authorName
  - Localized content: title, standfirst, metaTitle, metaDescription
  - Content blocks: Add blocks (HEADING, PARAGRAPH, QUOTE, BULLET_LIST, IMAGE, VIDEO, DOCUMENT)
  - Blocks are **localized per locale**
- Auto-translate articles and blocks
- Publish/unpublish articles

## CMS Sections

All Help Center pages use CMS sections for UI strings. Edit them in the Pages admin (`/admin/pages`).

### Section Types

#### `help_hero_v1`
Hero section with title, subtitle, and integrated search bar.
- **Fields**: `kicker`, `title`, `subtitle`, `placeholderSearch`, `helperText`, `backgroundStyle`
- **Translatable**: All text fields

#### `help_search_v1`
Standalone search bar (can also be embedded in hero).
- **Fields**: `placeholder`, `hint`, `clearLabel`, `noResultsTitle`, `noResultsSubtitle`
- **Translatable**: All fields

#### `help_collections_grid_v1`
Grid of collection cards (used on `/help` landing).
- **Fields**: `sectionTitle`, `sectionSubtitle`, `cardCtaLabel`, `articlesCountLabel`, `emptyTitle`, `emptySubtitle`
- **Translatable**: All fields

#### `help_collection_body_v1`
Shares-style layout showing categories and articles (used on `/help/[collection]`).
- **Fields**: `emptyCategoriesTitle`, `emptyCategoriesSubtitle`, `emptyArticlesTitle`, `emptyArticlesSubtitle`
- **Displays**:
  - Categories as stacked sections
  - Articles as clickable list items with chevrons
- **Translatable**: All empty state messages

#### `help_breadcrumbs_v1`
Breadcrumb navigation.
- **Fields**: `rootLabel`, `separator`
- **Translatable**: `rootLabel`

#### `help_article_reader_v1`
Article content renderer.
- **Fields**: `updatedLabel`, `byLabel`, `readingTimeLabel`, `relatedTitle`
- **Translatable**: All labels

#### `help_sidebar_toc_v1`
Table of contents sidebar.
- **Fields**: `tocTitle`
- **Translatable**: `tocTitle`

## Translation Workflow

### Auto-Translate
1. Edit content in source locale (default: `fr`)
2. Click "Auto-translate" button in admin
3. Select target locales (`en`, `it`)
4. Choose mode:
   - **Missing only**: Translate only empty/missing fields
   - **Force**: Retranslate all fields
5. Review and approve translations

### Translation Status
- `ORIGINAL` - Content in original locale
- `MACHINE` - Auto-translated, not yet approved
- `APPROVED` - Translation reviewed and approved

### Best Practices
- Always review machine translations before publishing
- Use glossary for consistent terminology
- Approve translations before publishing articles

## Search Functionality

### How It Works
1. User types in search bar (minimum 2 characters)
2. Debounce waits 300ms after last keystroke
3. API call to `/api/help/search` with:
   - `q`: search query
   - `locale`: current locale
   - `collection`: optional filter by collection
   - `category`: optional filter by category
4. Results appear in dropdown below search bar
5. Clicking result navigates to article

### What's Searched
- Article titles (`HelpArticleI18n.title`)
- Article standfirst (`HelpArticleI18n.standfirst`)
- Block content (`HelpArticleBlock.data` for PARAGRAPH, HEADING, QUOTE, BULLET_LIST)

### Search Scope
- Search from `/help`: Searches all published articles
- Search from `/help/[collection]`: Filters to that collection
- Search from `/help/[collection]/[category]`: Filters to that category

## Creating Help Content

### Step 1: Create Collection
1. Go to `/admin/help/collections`
2. Click "Add Collection"
3. Enter title (auto-generates slug)
4. Enter description
5. Set order
6. Save

### Step 2: Create Category
1. Go to `/admin/help/categories`
2. Filter by collection
3. Click "Add Category"
4. Select collection
5. Enter title (auto-generates slug)
6. Enter description
7. Set order
8. Save

### Step 3: Create Article
1. Go to `/admin/help/articles`
2. Click "Add Article"
3. Select collection and category
4. Enter title (auto-generates slug)
5. Edit article:
   - Add localized content (title, standfirst, meta)
   - Add content blocks (paragraphs, headings, images, etc.)
6. Save

### Step 4: Translate
1. Click "Auto-translate" on article
2. Select target locales
3. Review translations
4. Approve translations

### Step 5: Publish
1. Set article status to `PUBLISHED`
2. Verify translations are approved (warning shown if MACHINE)
3. Article appears on public site

## Content Blocks

Articles use the same block system as blog articles:

- **HEADING**: Section headings (generates TOC anchors)
- **PARAGRAPH**: Text paragraphs (supports Markdown)
- **QUOTE**: Block quotes
- **BULLET_LIST**: Bulleted lists
- **IMAGE**: Images with captions
- **VIDEO**: Embedded videos
- **DOCUMENT**: PDF/document attachments

**Important**: Blocks are **localized per locale**. When you add a block in FR, it doesn't automatically appear in EN/IT. Use "Auto-translate blocks" to translate block content.

## SEO & Metadata

Each article can have:
- `metaTitle`: SEO title (defaults to article title)
- `metaDescription`: SEO description (defaults to standfirst)

These are translatable and appear in the `<head>` of article pages.

## Troubleshooting

### Search Not Working
1. Check browser console for errors
2. Verify API endpoint is accessible: `/api/help/search?q=test&locale=fr`
3. Check that articles are `PUBLISHED` status
4. Verify articles have i18n content in target locale

### Articles Not Appearing
1. Check article status is `PUBLISHED`
2. Verify category is published
3. Verify collection is published
4. Check that article has i18n content in current locale

### Translations Not Appearing
1. Verify translation status in admin
2. Check that target locale has i18n records
3. Use "Missing only" mode to translate missing fields
4. Approve translations after reviewing

### Layout Issues
1. Verify CMS page exists (slug: `help`, `help-collection`, etc.)
2. Check that sections are configured in admin
3. Verify section content has published status
4. Check locale matches current page locale

## Best Practices

1. **Always publish collections/categories before articles** - Unpublished parents hide children
2. **Use descriptive slugs** - Auto-generated from titles, but can be edited
3. **Add meta descriptions** - Improves SEO and search result snippets
4. **Review translations** - Machine translations need human review
5. **Test on all locales** - Verify content appears correctly in FR/EN/IT
6. **Use consistent formatting** - Follow block structure for readability
7. **Add images/videos** - Visual content improves user experience









