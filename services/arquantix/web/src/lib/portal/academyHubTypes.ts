import type { PortalResearchItem } from '@/lib/portal/marketsTypes'

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
}

export type PortalAcademyHubPayload = {
  featured: PortalAcademyArticle | null
  highlighted: PortalAcademyArticle[]
  news: PortalAcademyArticle[]
  research: PortalResearchItem[]
}
