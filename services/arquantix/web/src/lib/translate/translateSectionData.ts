import type { TranslationOptions } from './types'
import { translateText } from './translateText'
import { translateMarkdown } from './translateMarkdown'

/**
 * Defines which fields are translatable for each section type
 * Format: "fieldPath" or "arrayField[].fieldPath" for nested arrays
 */
const SECTION_TRANSLATABLE_PATHS: Record<string, string[]> = {
  hero: ['title', 'subtitle', 'ctaText'],
  projects: ['title', 'description'],
  project_grid: ['title', 'description'],
  features: ['title', 'items[].title', 'items[].description'],
  about: ['title', 'description'],
  pricing: ['title', 'plans[].name', 'plans[].description'],
  footer: ['copyright'],
  blog_hero: ['eyebrow'],
  blog_category_nav: ['title', 'allLabel'],
  blog_mosaic: ['title'],
  blog_feed: ['title', 'loadMoreLabel', 'emptyStateTitle', 'emptyStateBody'],
  faq: ['title', 'subtitle', 'items[].question', 'items[].answerMarkdown'],
  // Help Center sections
  help_hero_v1: ['kicker', 'title', 'subtitle', 'placeholderSearch', 'helperText'],
  help_search_v1: ['placeholder', 'hint', 'clearLabel', 'noResultsTitle', 'noResultsSubtitle'],
  help_collections_grid_v1: ['sectionTitle', 'sectionSubtitle', 'cardCtaLabel', 'articlesCountLabel', 'emptyTitle', 'emptySubtitle'],
  help_categories_grid_v1: ['sectionTitle', 'sectionSubtitle', 'articlesCountLabel', 'emptyTitle', 'emptySubtitle'],
  help_collection_body_v1: ['emptyCategoriesTitle', 'emptyCategoriesSubtitle', 'emptyArticlesTitle', 'emptyArticlesSubtitle'],
  help_breadcrumbs_v1: ['rootLabel', 'separator'],
  help_search_results_v1: ['resultsTitle', 'resultsCountLabel', 'emptyTitle', 'emptySubtitle'],
  help_article_reader_v1: ['updatedLabel', 'byLabel', 'readingTimeLabel', 'relatedTitle'],
  help_sidebar_toc_v1: ['tocTitle'],
  // Add more section types as needed
}

/**
 * Get value at path in object (supports nested paths and arrays)
 */
function getValueAtPath(obj: any, path: string): any {
  // Handle simple field names (no dots)
  if (!path.includes('.')) {
    return obj && typeof obj === 'object' && path in obj ? obj[path] : null
  }

  const parts = path.split('.')
  let current = obj

  for (const part of parts) {
    if (part.includes('[]')) {
      const [arrayKey, ...rest] = part.split('[]')
      if (current[arrayKey] && Array.isArray(current[arrayKey])) {
        // For array paths, we'll handle them in translateSectionData
        return null // Signal that this is an array path
      }
      return null
    }
    if (current && typeof current === 'object' && part in current) {
      current = current[part]
    } else {
      return null
    }
  }

  return current
}

/**
 * Set value at path in object (supports nested paths and arrays)
 */
function setValueAtPath(obj: any, path: string, value: any): void {
  // Handle simple field names (no dots)
  if (!path.includes('.')) {
    if (obj && typeof obj === 'object') {
      obj[path] = value
    }
    return
  }

  const parts = path.split('.')
  let current = obj

  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i]
    if (part.includes('[]')) {
      const [arrayKey] = part.split('[]')
      if (!current[arrayKey]) {
        current[arrayKey] = []
      }
      // Array paths are handled separately
      return
    }
    if (!(part in current) || typeof current[part] !== 'object' || current[part] === null) {
      current[part] = {}
    }
    current = current[part]
  }

  const lastPart = parts[parts.length - 1]
  if (lastPart.includes('[]')) {
    const [arrayKey] = lastPart.split('[]')
    if (!current[arrayKey]) {
      current[arrayKey] = []
    }
    // Array handling is done in translateSectionData
    return
  }
  current[lastPart] = value
}

/**
 * Translate section data JSON
 * Only translates known text fields, preserves structure
 */
export async function translateSectionData(
  data: any,
  sectionKey: string,
  options: TranslationOptions
): Promise<any> {
  // Get translatable paths for this section type
  const translatablePaths = SECTION_TRANSLATABLE_PATHS[sectionKey] || []

  if (translatablePaths.length === 0) {
    // Unknown section type - return original data unchanged
    console.warn(`No translatable paths defined for section type: ${sectionKey}`)
    return data
  }

  // Deep clone to avoid mutating original
  // Use structuredClone if available (Node 18+), fallback to JSON for compatibility
  const translated =
    typeof structuredClone !== 'undefined'
      ? structuredClone(data)
      : JSON.parse(JSON.stringify(data))

  // Translate each path
  for (const path of translatablePaths) {
    if (path.includes('[]')) {
      // Handle array paths (e.g., "items[].title", "items[].answerMarkdown")
      const [arrayKey, ...fieldParts] = path.split('[]')
      const fieldPath = fieldParts.join('[]').replace(/^\./, '')

      if (translated[arrayKey] && Array.isArray(translated[arrayKey])) {
        for (let i = 0; i < translated[arrayKey].length; i++) {
          const item = translated[arrayKey][i]
          if (item && typeof item === 'object') {
            // Get field value (handle both simple and nested paths)
            const fieldValue = getValueAtPath(item, fieldPath)

            if (fieldValue && typeof fieldValue === 'string' && fieldValue.trim().length > 0) {
              try {
                // Use translateMarkdown for markdown fields, translateText for others
                const isMarkdownField = fieldPath.toLowerCase().includes('markdown')
                
                if (process.env.NODE_ENV !== 'production') {
                  console.log(
                    `[Translate][FAQ] Translating ${path}[${i}]: fieldPath="${fieldPath}", isMarkdown=${isMarkdownField}, valueLength=${fieldValue.length}`
                  )
                }
                
                const result = isMarkdownField
                  ? await translateMarkdown(fieldValue, options)
                  : await translateText(fieldValue, options)
                
                // Set the translated value
                setValueAtPath(item, fieldPath, result.translated)
                
                if (process.env.NODE_ENV !== 'production') {
                  console.log(
                    `[Translate][FAQ] Translated ${path}[${i}]: "${fieldValue.substring(0, 50)}..." -> "${result.translated.substring(0, 50)}..."`
                  )
                }
              } catch (error) {
                console.error(`Error translating ${path}[${i}]:`, error)
                // Keep original value on error
              }
            } else {
              if (process.env.NODE_ENV !== 'production') {
                console.log(
                  `[Translate][FAQ] Skipping ${path}[${i}]: fieldValue=${fieldValue}, type=${typeof fieldValue}`
                )
              }
            }
          }
        }
      } else {
        if (process.env.NODE_ENV !== 'production') {
          console.log(
            `[Translate][FAQ] No array found for ${arrayKey} or it's not an array`
          )
        }
      }
    } else {
      // Handle simple paths (e.g., "title")
      const value = getValueAtPath(translated, path)
      if (value && typeof value === 'string' && value.trim().length > 0) {
        try {
          const result = await translateText(value, options)
          setValueAtPath(translated, path, result.translated)
        } catch (error) {
          console.error(`Error translating ${path}:`, error)
          // Keep original value on error
        }
      }
    }
  }

  return translated
}

