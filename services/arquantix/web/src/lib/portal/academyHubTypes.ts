import type { AppNewsCategoryDot } from '@/components/design-system/app/AppNewsStackedList'
import type { PortalResearchItem } from '@/lib/portal/marketsTypes'

export type PortalAcademyCategory = {
  id: string
  slug: string
  label: string
}

export type PortalAcademyArticle = {
  id: string
  slug: string
  title: string
  standfirst: string
  coverUrl: string
  authorName: string
  publishedAt: string | null
  readingTime: number
  href: string
  categorySlug: string | null
  categoryLabel: string | null
  categoryTone: AppNewsCategoryDot
  articleType: 'NEWS' | 'ANALYSIS' | 'RESEARCH'
}

export type PortalAcademyHubPayload = {
  featured: PortalAcademyArticle | null
  highlighted: PortalAcademyArticle[]
  news: PortalAcademyArticle[]
  research: PortalResearchItem[]
  categories: PortalAcademyCategory[]
}
