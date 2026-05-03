/**
 * Utility function to slugify a string
 * Converts to lowercase, removes special chars, replaces spaces with hyphens
 */

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // Remove accents
    .replace(/[^a-z0-9\s-]/g, '') // Remove special characters except spaces and hyphens
    .replace(/\s+/g, '-') // Replace spaces with hyphens
    .replace(/-+/g, '-') // Replace multiple hyphens with single hyphen
    .replace(/^-+|-+$/g, '') // Remove leading/trailing hyphens
}

/**
 * Validate slug format
 * - lowercase
 * - a-z0-9- only
 * - no spaces
 * - max 255 chars (aligné DB / URLs longues, ex. titres presse)
 */
export function isValidSlug(slug: string): boolean {
  if (slug.length === 0 || slug.length > 255) {
    return false
  }
  // Must match: lowercase letters, numbers, and hyphens only
  const slugRegex = /^[a-z0-9-]+$/
  return slugRegex.test(slug)
}

/**
 * Calculate urlPath from slug
 * "/" for "home", otherwise "/<slug>"
 */
export function calculateUrlPath(slug: string): string {
  if (slug === 'home') {
    return '/'
  }
  return `/${slug}`
}

/**
 * URL publique canonique pour une page **Vault Builder / offre exclusive** : sous `/projects/[slug]`.
 * (Les pages CMS classiques continuent d’utiliser `calculateUrlPath`.)
 */
export function calculateExclusiveOfferPageUrlPath(slug: string): string {
  if (slug === 'home') {
    return '/'
  }
  return `/projects/${slug}`
}









