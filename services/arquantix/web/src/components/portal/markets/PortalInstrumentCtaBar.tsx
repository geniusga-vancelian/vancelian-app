'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'

type Props = {
  buyHref?: string
  sellHref?: string
  canSell: boolean
}

/** Barre d'actions principale — handoff `.ast-cta`. */
export function PortalInstrumentCtaBar({ buyHref, sellHref, canSell }: Props) {
  return (
    <div className="ast-cta">
      {buyHref ? (
        <PortalNavLink href={buyHref} className="btn btn--primary btn--lg no-underline">
          <KalaiIcon name="arrow-down" size={16} />
          Acheter
        </PortalNavLink>
      ) : (
        <button type="button" className="btn btn--primary btn--lg" disabled>
          <KalaiIcon name="arrow-down" size={16} />
          Acheter
        </button>
      )}
      {sellHref && canSell ? (
        <PortalNavLink href={sellHref} className="btn btn--secondary btn--lg no-underline">
          <KalaiIcon name="arrow-up" size={16} />
          Vendre
        </PortalNavLink>
      ) : (
        <button type="button" className="btn btn--secondary btn--lg" disabled={!canSell}>
          <KalaiIcon name="arrow-up" size={16} />
          Vendre
        </button>
      )}
    </div>
  )
}
