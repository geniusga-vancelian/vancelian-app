export type PortalExclusiveOffer = {
  id: string
  slug: string
  title: string
  subtitle: string
  coverUrl: string
  category: string
  description: string
  progressPct: number
  raisedLabel: string
  targetLabel: string
  investorsCount: number
  apyLabel: string
  durationMonths: number | null
  isFunded: boolean
  href: string
}

export type PortalInvestPayload = {
  heroImageUrl: string | null
  heroTitle: string
  heroSubtitle: string
  offers: PortalExclusiveOffer[]
}
