'use client'

import { PortalInstrumentHoldingCard } from '@/components/portal/markets/PortalInstrumentHoldingCard'
import { PortalInstrumentKeyStatsCard } from '@/components/portal/markets/PortalInstrumentKeyStatsCard'

type Props = {
  ticker: string
  priceUsd: number
  sidebarStats: Array<{ key: string; value: string }>
  buyHref?: string
  sellHref?: string
}

/** Colonne latérale fiche actif — position + statistiques. */
export function PortalInstrumentSidebar({
  ticker,
  priceUsd,
  sidebarStats,
  buyHref,
  sellHref,
}: Props) {
  return (
    <div className="ast-side-stack">
      <PortalInstrumentHoldingCard
        ticker={ticker}
        priceUsd={priceUsd}
        buyHref={buyHref}
        sellHref={sellHref}
      />
      <PortalInstrumentKeyStatsCard stats={sidebarStats} />
    </div>
  )
}
