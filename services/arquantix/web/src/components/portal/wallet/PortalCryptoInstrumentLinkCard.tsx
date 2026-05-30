'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { portalCryptoInstrumentRoute } from '@/lib/portal/portalRouting'

type Props = {
  ticker: string
  assetName: string
}

/** Product sheet link — handoff Position.html `.pos-product` (crypto → markets instrument). */
export function PortalCryptoInstrumentLinkCard({ ticker, assetName }: Props) {
  const href = portalCryptoInstrumentRoute(ticker)

  return (
    <PortalNavLink href={href} className="pos-product no-underline">
      <div className="pos-product__body">
        <span className="pos-product__eyebrow">Product sheet</span>
        <h3 className="pos-product__title">View {assetName} market page</h3>
        <p className="pos-product__sub">
          Full description, live chart, extended market stats and research.
        </p>
      </div>
      <span className="pos-product__chv" aria-hidden>
        <KalaiIcon name="arrow-up-right" size={16} />
      </span>
    </PortalNavLink>
  )
}
