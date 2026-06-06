'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { portalExclusiveOfferRoute } from '@/lib/portal/portalRouting'

type Props = {
  slug: string
  vaultName: string
}

/** Lien fiche produit — handoff Position.html `.pos-product`. */
export function PortalSavingsVaultProductLink({ slug, vaultName }: Props) {
  const href = portalExclusiveOfferRoute(slug)

  return (
    <PortalNavLink href={href} className="pos-product no-underline">
      <div className="pos-product__body">
        <span className="pos-product__eyebrow">Fiche produit</span>
        <h3 className="pos-product__title">Voir la fiche du coffre</h3>
        <p className="pos-product__sub">{vaultName} — description, méthodologie et conditions.</p>
      </div>
      <span className="pos-product__chv" aria-hidden="true">
        <KalaiIcon name="arrow-up-right" size={16} />
      </span>
    </PortalNavLink>
  )
}
