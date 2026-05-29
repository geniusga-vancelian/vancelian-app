import type { PortalAcademyArticle, PortalAcademyHubPayload } from '@/lib/portal/academyHubTypes'
import { sanitizePortalArticleClientHref } from '@/lib/portal/portalArticleRouting'

function sanitizeArticle(article: PortalAcademyArticle): PortalAcademyArticle {
  return { ...article, href: sanitizePortalArticleClientHref(article.href) }
}

/** Dernier filet avant JSON — aucun href loopback ne doit atteindre le client. */
export function sanitizeAcademyHubPayload(payload: PortalAcademyHubPayload): PortalAcademyHubPayload {
  return {
    featured: payload.featured ? sanitizeArticle(payload.featured) : null,
    highlighted: payload.highlighted.map(sanitizeArticle),
    marketNews: payload.marketNews.map(sanitizeArticle),
    vancelianNews: payload.vancelianNews.map(sanitizeArticle),
    analysis: payload.analysis.map(sanitizeArticle),
    academy: payload.academy.map(sanitizeArticle),
  }
}
