import { getLocaleOrDefault } from '@/config/locales'

/** URL canonique publique d’un article blog (partage / Open Graph). */
export function publicArticlePageUrl(locale: string, slug: string): string {
  const loc = getLocaleOrDefault(locale)
  const path = `/${loc}/blog/${slug}`
  try {
    return new URL(path, process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000').href
  } catch {
    return path
  }
}
