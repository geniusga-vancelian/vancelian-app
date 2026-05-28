'use client'

import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

const MARKET_INDICES = [
  { sym: 'CAC 40', price: '8 214,30', chg: 0.62 },
  { sym: 'S&P 500', price: '5 842,10', chg: 1.18 },
  { sym: 'EUR / USD', price: '1,0842', chg: -0.21 },
  { sym: 'Or', price: '2 358,40', chg: 0.84, unit: '/ oz' },
] as const

function formatIndexChange(chg: number): string {
  const sign = chg >= 0 ? '+ ' : '− '
  return `${sign}${Math.abs(chg).toFixed(2).replace('.', ',')} %`
}

function PortalMarketsIndicesCard() {
  return (
    <div className="mk-side-card">
      <div className="mk-side-card__eyebrow">Indices</div>
      <div>
        {MARKET_INDICES.map((idx) => {
          const up = idx.chg >= 0
          return (
            <div key={idx.sym} className="mk-idx-row">
              <span className="mk-idx-row__name">{idx.sym}</span>
              <span className="mk-idx-row__price">
                {idx.price}
                {'unit' in idx && idx.unit ? `\u00a0${idx.unit}` : ''}
              </span>
              <span className={cn('mk-idx-row__chg', up ? 'mk-idx-row__chg--up' : 'mk-idx-row__chg--down')}>
                {formatIndexChange(idx.chg)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function PortalMarketsWatchlistBanner() {
  return (
    <PortalNavLink href={PORTAL_ROUTES.marketsAllCrypto} className="mk-watch no-underline">
      <span className="mk-watch__ic" aria-hidden>
        <KalaiIcon name="star" size={16} />
      </span>
      <span className="mk-watch__body">
        <span className="mk-watch__title">Suivez vos actifs préférés</span>
        <span className="mk-watch__sub">
          Ajoutez-les depuis chaque fiche pour les retrouver ici.
        </span>
      </span>
    </PortalNavLink>
  )
}

/** Sidebar marchés — handoff Marches.html (indices · watchlist · advisor). */
export function PortalMarketsSidebar() {
  return (
    <>
      <PortalMarketsIndicesCard />
      <PortalMarketsWatchlistBanner />
      <PortalAdvisorBanner />
    </>
  )
}
