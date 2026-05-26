import type { PublicArticle } from '@/lib/blog/getPublicArticle'
import type { NormalizedArticleBlock } from '@/lib/blog/normalizeArticleBlocks'

export type PortalAcademyArticleView = {
  kind: 'academy'
  slug: string
  title: string
  standfirst: string | null
  authorName: string
  publishedAt: Date | null
  createdAt: Date
  updatedAt: Date
  coverUrl: string
  blocks: NormalizedArticleBlock[]
  documents: PublicArticle['documents']
  articleType: 'ACADEMY'
  collectionTitle: string
  categoryTitle: string
  locale: string
}

export type PortalEditorialArticleView = {
  kind: 'editorial'
  article: PublicArticle
}

export type PortalArticleView = PortalEditorialArticleView | PortalAcademyArticleView

export function portalArticleTypeLabel(view: PortalArticleView): string {
  if (view.kind === 'academy') return 'Academy'
  const type = (view.article.articleType || 'NEWS').toUpperCase()
  if (type === 'ANALYSIS' || type === 'RESEARCH') return 'Research'
  if (view.article.isCompanyNews) return 'News'
  return 'News'
}
