import type { PortalAcademyArticle } from '@/lib/portal/academyHubTypes'

export type PortalAcademyEditorialTabId =
  | 'market-news'
  | 'vancelian-news'
  | 'analysis'
  | 'academy'

export const PORTAL_ACADEMY_EDITORIAL_TABS: Array<{ id: PortalAcademyEditorialTabId; label: string }> =
  [
    { id: 'market-news', label: 'Market News' },
    { id: 'vancelian-news', label: 'Vancelian News' },
    { id: 'analysis', label: 'Analysis' },
    { id: 'academy', label: 'Academy' },
  ]

export const PORTAL_ACADEMY_DEFAULT_TAB: PortalAcademyEditorialTabId = 'market-news'

export function articleMatchesAcademyEditorialTab(
  article: PortalAcademyArticle,
  tabId: PortalAcademyEditorialTabId,
): boolean {
  switch (tabId) {
    case 'market-news':
      return article.articleType === 'NEWS' && !article.isCompanyNews
    case 'vancelian-news':
      return article.articleType === 'NEWS' && article.isCompanyNews
    case 'analysis':
      return article.articleType === 'ANALYSIS'
    case 'academy':
      return article.articleType === 'ACADEMY'
    default:
      return false
  }
}

export function buildAcademyHubCatalog(payload: {
  marketNews: PortalAcademyArticle[]
  vancelianNews: PortalAcademyArticle[]
  analysis: PortalAcademyArticle[]
  academy: PortalAcademyArticle[]
}): PortalAcademyArticle[] {
  const byId = new Map<string, PortalAcademyArticle>()
  for (const article of [
    ...payload.marketNews,
    ...payload.vancelianNews,
    ...payload.analysis,
    ...payload.academy,
  ]) {
    if (!byId.has(article.id)) byId.set(article.id, article)
  }
  return [...byId.values()]
}
