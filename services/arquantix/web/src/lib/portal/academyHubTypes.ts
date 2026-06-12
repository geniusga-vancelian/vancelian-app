import type { AppNewsCategoryDot } from '@/components/design-system/app/AppNewsStackedList'

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
  articleType: 'NEWS' | 'ANALYSIS' | 'RESEARCH' | 'ACADEMY'
  /** Actualités entreprise (NEWS uniquement). */
  isCompanyNews: boolean
}

export type PortalAcademyHubPayload = {
  featured: PortalAcademyArticle | null
  highlighted: PortalAcademyArticle[]
  marketNews: PortalAcademyArticle[]
  vancelianNews: PortalAcademyArticle[]
  analysis: PortalAcademyArticle[]
  academy: PortalAcademyArticle[]
}

/** Section éditoriale Academy (actualités marché/entreprise + analyses) — rapide. */
export type PortalAcademyEditorialPayload = {
  featured: PortalAcademyArticle | null
  highlighted: PortalAcademyArticle[]
  marketNews: PortalAcademyArticle[]
  vancelianNews: PortalAcademyArticle[]
  analysis: PortalAcademyArticle[]
  partial?: boolean
}

/** Section bibliothèque Academy (articles pédagogiques CMS). */
export type PortalAcademyLibraryPayload = {
  academy: PortalAcademyArticle[]
  partial?: boolean
}
