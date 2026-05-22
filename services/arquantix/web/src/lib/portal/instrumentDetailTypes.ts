import type { PortalMarketsNewsItem, PortalResearchItem } from '@/lib/portal/marketsTypes'

export type PortalInstrumentDetailPayload = {
  ticker: string
  symbol: string
  name: string
  priceUsd: number
  priceLabel: string
  change24hPct: number
  change24hAbs: number | null
  logoUrl: string | null
  instrumentId: number | null
  news: PortalMarketsNewsItem[]
  research: PortalResearchItem[]
  marketDataPublicBaseUrl: string
  partial?: boolean
}
