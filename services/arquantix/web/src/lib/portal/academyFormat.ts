import type { AppNewsCategoryDot } from '@/components/design-system/app/AppNewsStackedList'
import type { PortalAcademyArticle } from '@/lib/portal/academyHubTypes'
import type { PortalResearchItem } from '@/lib/portal/marketsTypes'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'

export function normalizeAcademySearch(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
}

export function formatAcademyReadTime(minutes: number): string {
  const m = Math.max(1, Math.round(minutes))
  return `${m} min read`
}

export function academyCategoryTone(slug: string | null | undefined): AppNewsCategoryDot {
  if (!slug) return 'ink'
  let h = 0
  for (let i = 0; i < slug.length; i += 1) {
    h = (h * 31 + slug.charCodeAt(i)) >>> 0
  }
  const tones: AppNewsCategoryDot[] = ['terra', 'green', 'blue', 'ink']
  return tones[h % tones.length] ?? 'ink'
}

export function academySectionLabel(article: PortalAcademyArticle): string {
  if (article.articleType === 'ACADEMY') return 'Academy'
  if (article.articleType === 'ANALYSIS' || article.articleType === 'RESEARCH') return 'Analysis'
  if (article.isCompanyNews) return 'Vancelian News'
  return 'Market News'
}

export function academyArticleMatchesSearch(article: PortalAcademyArticle, query: string): boolean {
  const q = normalizeAcademySearch(query).trim()
  if (!q) return true
  const haystack = [
    article.title,
    article.standfirst,
    article.authorName,
    article.categoryLabel ?? '',
    academySectionLabel(article),
  ]
    .map(normalizeAcademySearch)
    .join(' ')
  return haystack.includes(q)
}

export function academyArticlePublishedLabel(
  article: PortalAcademyArticle,
  locale = PORTAL_CONTENT_LOCALE,
): string | null {
  if (!article.publishedAt) return null
  return formatArticleDateShort(new Date(article.publishedAt), locale)
}

export function researchToAcademyArticle(item: PortalResearchItem): PortalAcademyArticle {
  return {
    id: item.id,
    slug: item.href.split('/').filter(Boolean).pop() ?? item.id,
    title: item.title,
    standfirst: '',
    coverUrl: item.coverUrl,
    authorName: 'Vancelian',
    publishedAt: null,
    readingTime: item.readingTime,
    href: item.href,
    categorySlug: 'analysis',
    categoryLabel: item.tag?.trim() || 'Analysis',
    categoryTone: 'blue',
    articleType: 'ANALYSIS',
    isCompanyNews: false,
  }
}

export function buildAcademyPagerPages(page: number, pageCount: number): Array<number | '…'> {
  if (pageCount <= 7) {
    return Array.from({ length: pageCount }, (_, index) => index + 1)
  }
  if (page <= 4) return [1, 2, 3, 4, 5, '…', pageCount]
  if (page >= pageCount - 3) {
    return [1, '…', pageCount - 4, pageCount - 3, pageCount - 2, pageCount - 1, pageCount]
  }
  return [1, '…', page - 1, page, page + 1, '…', pageCount]
}
