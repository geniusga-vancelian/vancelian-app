'use client'

import { useMemo } from 'react'
import { useRouter } from 'next/navigation'

import {
  isPlacerCoffreBundle,
  PortalPlacerBasketCard,
  PortalPlacerBundleCoffreCard,
  PortalPlacerSectionHead,
} from '@/components/portal/bundles/PortalPlacerBundleCards'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { resolvePortalBundleFlowRoute } from '@/lib/portal/resolvePortalBundleFlowRoute'

type Props = {
  bundles: PortalCryptoBundle[]
}

/** Vaults + crypto baskets — Placer.html ; invest → page dédiée (comme swap), pas de modale. */
export function PortalCryptoBundlesSection({ bundles }: Props) {
  const router = useRouter()

  const openBundleInvest = (bundle: PortalCryptoBundle) => {
    const href = resolvePortalBundleFlowRoute(bundle, 'invest', { from: 'markets' })
    if (href) router.push(href)
  }

  const { coffreBundles, panierBundles } = useMemo(() => {
    const coffres = bundles.filter(isPlacerCoffreBundle)
    const paniers = bundles.filter((bundle) => !isPlacerCoffreBundle(bundle))
    return { coffreBundles: coffres, panierBundles: paniers }
  }, [bundles])

  if (bundles.length === 0) return null

  return (
    <div className="flex flex-col gap-10">
      {coffreBundles.length > 0 ? (
        <div className="placer-section">
          <PortalPlacerSectionHead
            title="Vaults"
            desc="A productive reserve, matched to your time horizon."
          />
          <div className="placer-grid placer-grid--2">
            {coffreBundles.map((bundle) => (
              <PortalPlacerBundleCoffreCard
                key={bundle.id}
                bundle={bundle}
                onInvest={() => openBundleInvest(bundle)}
              />
            ))}
          </div>
        </div>
      ) : null}

      {panierBundles.length > 0 ? (
        <div className="placer-section">
          <PortalPlacerSectionHead
            title="Crypto baskets"
            desc="Thematic exposures rebalanced every month."
          />
          <div className="placer-grid placer-grid--2">
            {panierBundles.map((bundle) => (
              <PortalPlacerBasketCard
                key={bundle.id}
                bundle={bundle}
                onInvest={() => openBundleInvest(bundle)}
              />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
