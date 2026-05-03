import { slugify, isValidSlug } from '@/lib/utils/slugify'

/**
 * Tags de regroupement sous une collection (Help, Academy, ou autres types).
 * Stockés en JSON (tableau de slugs) sur `Article.collection_tags`.
 */
export function parseCollectionTags(raw: unknown): string[] {
  let source: unknown = raw
  if (typeof source === 'string') {
    try {
      source = JSON.parse(source)
    } catch {
      return []
    }
  }
  if (!Array.isArray(source)) return []
  const out: string[] = []
  const seen = new Set<string>()
  for (const item of source) {
    if (typeof item !== 'string') continue
    const s = slugify(item)
    if (!s || !isValidSlug(s)) continue
    if (!seen.has(s)) {
      seen.add(s)
      out.push(s)
    }
  }
  return out
}

/** Normalise une liste déjà « slash » / tirets pour persistance. */
export function normalizeCollectionTagsList(tags: string[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const t of tags) {
    const s = slugify(String(t || ''))
    if (!s || !isValidSlug(s)) continue
    if (!seen.has(s)) {
      seen.add(s)
      out.push(s)
    }
  }
  return out
}

/** Libellé lisible pour affichage (titres de sections Help). */
export function tagSlugToDisplayTitle(slug: string): string {
  if (!slug.trim()) return slug
  return slug
    .split('-')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

/** Premier niveau de regroupement sous une collection (tags JSON ou FK catégorie legacy). */
export function deriveGroupingTags(
  collectionTagsJson: unknown,
  fallbackCategorySlug: string | null,
): string[] {
  const fromJson = parseCollectionTags(collectionTagsJson)
  if (fromJson.length > 0) return fromJson
  if (fallbackCategorySlug) return [fallbackCategorySlug]
  return ['general']
}
