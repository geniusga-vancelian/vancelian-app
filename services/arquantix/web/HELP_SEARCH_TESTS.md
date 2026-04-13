# Help Center Search - Manual Test Checklist

## Prerequisites
- Help Center collections, categories, and articles should be seeded
- At least one published article in FR locale
- Server running in development mode (logs enabled)

## Test Cases

### 1. Basic Search from `/help`
- [ ] Navigate to `/help`
- [ ] Type at least 2 characters in the search bar (e.g., "liste")
- [ ] Verify that:
  - Debounce works (300ms delay before request)
  - Console shows debug logs: `[SectionHelpSearch] Performing search:`
  - API request is made to `/api/help/search?q=...&locale=fr`
  - Results appear below search bar in a dropdown
  - Results show article title, snippet, collection/category breadcrumbs
  - Clicking a result navigates to the article page

### 2. Search from `/help/[collection]`
- [ ] Navigate to a collection page (e.g., `/help/getting-started`)
- [ ] Type a search query
- [ ] Verify that:
  - Results are filtered to that collection only
  - API request includes `collection=...` parameter
  - Console logs show `collectionSlug` in debug output

### 3. Search from `/help/[collection]/[category]`
- [ ] Navigate to a category page (e.g., `/help/getting-started/account-setup`)
- [ ] Type a search query
- [ ] Verify that:
  - Results are filtered to that category only
  - API request includes both `collection=...` and `category=...` parameters
  - Console logs show both `collectionSlug` and `categorySlug`

### 4. Clear Functionality
- [ ] Type a search query
- [ ] Click the X button (clear button)
- [ ] Verify that:
  - Query input is cleared
  - Results dropdown disappears
  - URL query parameter `q` is removed
  - No API request is made after clearing

### 5. Empty Results
- [ ] Type a query that matches no articles (e.g., "xyzabc123")
- [ ] Verify that:
  - Empty state message appears: "Aucun résultat" / "Essayez un autre mot-clé."
  - No results are shown
  - Error state is NOT shown (empty is different from error)

### 6. Non-ASCII Characters
- [ ] Type a search query with special characters (e.g., "créer", "réponse", "étapes")
- [ ] Verify that:
  - Query is properly encoded in URL
  - API receives correct query (check console logs)
  - Results match correctly (case-insensitive, accent-insensitive if possible)

### 7. Locale Switching (EN/IT)
- [ ] Change locale cookie to `en` or `it`
- [ ] Navigate to `/help`
- [ ] Type a search query
- [ ] Verify that:
  - API request includes correct `locale=...` parameter
  - Results show localized article titles/standfirst
  - Snippets are in the correct locale
  - Empty state messages are in correct locale (if implemented)

### 8. Minimum Query Length
- [ ] Type 1 character
- [ ] Verify that NO API request is made
- [ ] Type 2 characters
- [ ] Verify that API request IS made

### 9. Form Submit (Enter Key)
- [ ] Type a search query
- [ ] Press Enter
- [ ] Verify that:
  - Form submit handler fires (check console logs)
  - URL is updated with `?q=...` parameter
  - Search is performed
  - Results are shown

### 10. API Error Handling
- [ ] Stop the server or cause API error
- [ ] Type a search query
- [ ] Verify that:
  - Error message appears: "Erreur lors de la recherche. Veuillez réessayer."
  - Results dropdown is hidden
  - Console shows error details in dev mode

## Expected Console Logs (Development Mode)

When working correctly, you should see:

```
[SectionHelpSearch] Input changed: <query>
[SectionHelpSearch] Performing search: { query: "...", locale: "fr", ... }
[SectionHelpSearch] Fetching: /api/help/search?q=...&locale=fr&...
[Help Search API] Starting search: { query: "...", locale: "fr", ... }
[Help Search API] Found X articles to search through
[Help Search API] Search completed: { totalMatches: X, limitedResults: Y, query: "..." }
[SectionHelpSearch] Search completed: { resultsCount: Y, query: "...", hasError: false }
```

## Known Issues / Limitations
- Debounce is 300ms (may feel slightly delayed)
- Search is case-insensitive but accent-sensitive (PostgreSQL default)
- Maximum 50 results returned (limit parameter)
- Only PUBLISHED articles are searched

## Notes
- All debug logs are guarded by `NODE_ENV !== 'production'`
- In production, console logs will be silent
- Search works on client-side only (no SSR for results)
- Results are shown in a dropdown, not a separate page
