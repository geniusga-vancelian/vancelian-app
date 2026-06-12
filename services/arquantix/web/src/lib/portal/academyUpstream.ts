import {
  mapAcademyHubFromBlogFeed,
  mapAnalysisFromBlogFeed,
  mapVancelianNewsFromBlogFeed,
} from '@/lib/portal/mapAcademyHubFeed'
import type {
  PortalAcademyArticle,
  PortalAcademyEditorialPayload,
  PortalAcademyLibraryPayload,
} from '@/lib/portal/academyHubTypes'
import { listPortalAcademyTypeArticles } from '@/lib/portal/listPortalAcademyArticles'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { sanitizePortalArticleClientHref } from '@/lib/portal/portalArticleRouting'

export const PORTAL_ACADEMY_FETCH_TIMEOUT_MS = 30_000

async function fetchJsonSafe(url: string) {
  try {
    const res = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(PORTAL_ACADEMY_FETCH_TIMEOUT_MS),
    })
    const data = await res.json().catch(() => null)
    return { ok: res.ok, data }
  } catch {
    return { ok: false, data: null }
  }
}

function sanitizeArticle(article: PortalAcademyArticle): PortalAcademyArticle {
  return { ...article, href: sanitizePortalArticleClientHref(article.href) }
}

/** Section éditoriale : actualités marché + entreprise + analyses (3 feeds blog). */
export async function loadPortalAcademyEditorial(
  bffOrigin: string,
  locale: string = PORTAL_CONTENT_LOCALE,
): Promise<PortalAcademyEditorialPayload> {
  const blogQuery = (segment: string, pageSize: number) =>
    `${bffOrigin}/api/blog?locale=${encodeURIComponent(locale)}&page=1&pageSize=${pageSize}&segment=${segment}`

  const [marketRes, companyRes, analysisRes] = await Promise.all([
    fetchJsonSafe(blogQuery('market', 24)),
    fetchJsonSafe(blogQuery('company', 24)),
    fetchJsonSafe(blogQuery('analysis', 24)),
  ])

  const marketHub = mapAcademyHubFromBlogFeed(marketRes.data)
  const vancelianNews = mapVancelianNewsFromBlogFeed(companyRes.data)
  const analysis = mapAnalysisFromBlogFeed(analysisRes.data)

  return {
    featured: marketHub.featured ? sanitizeArticle(marketHub.featured) : null,
    highlighted: marketHub.highlighted.map(sanitizeArticle),
    marketNews: marketHub.marketNews.map(sanitizeArticle),
    vancelianNews: vancelianNews.map(sanitizeArticle),
    analysis: analysis.map(sanitizeArticle),
    partial: !marketRes.ok || !companyRes.ok || !analysisRes.ok,
  }
}

/** Section bibliothèque : articles pédagogiques (CMS interne). */
export async function loadPortalAcademyLibrary(
  locale: string = PORTAL_CONTENT_LOCALE,
): Promise<PortalAcademyLibraryPayload> {
  try {
    const academy = await listPortalAcademyTypeArticles(locale, { limit: 48 })
    return { academy: academy.map(sanitizeArticle) }
  } catch (error) {
    console.error('[loadPortalAcademyLibrary]', error)
    return { academy: [], partial: true }
  }
}
