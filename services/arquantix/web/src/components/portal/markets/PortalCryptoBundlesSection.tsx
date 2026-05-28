'use client'

import { useMemo, useState } from 'react'

import { PortalBundleInvestDialog } from '@/components/portal/bundles/PortalBundleInvestDialog'
import {
  isPlacerCoffreBundle,
  PortalPlacerBasketCard,
  PortalPlacerBundleCoffreCard,
  PortalPlacerSectionHead,
} from '@/components/portal/bundles/PortalPlacerBundleCards'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'

type Props = {
  bundles: PortalCryptoBundle[]
}

/** Coffres + paniers crypto — aligné Vault Builder (titre · description · CTA). */
export function PortalCryptoBundlesSection({ bundles }: Props) {
  const [investBundle, setInvestBundle] = useState<PortalCryptoBundle | null>(null)

  const { coffreBundles, panierBundles } = useMemo(() => {
    const coffres = bundles.filter(isPlacerCoffreBundle)
    const paniers = bundles.filter((bundle) => !isPlacerCoffreBundle(bundle))
    return { coffreBundles: coffres, panierBundles: paniers }
  }, [bundles])

  if (bundles.length === 0) return null

  return (
    <div className="flex flex-col gap-10">
      {coffreBundles.length > 0 ? (
        <section>
          <PortalPlacerSectionHead
            title="Coffres"
            desc="Une réserve productive, choisie selon votre horizon."
          />
          <div className="placer-grid placer-grid--2">
            {coffreBundles.map((bundle) => (
              <PortalPlacerBundleCoffreCard
                key={bundle.id}
                bundle={bundle}
                onInvest={() => setInvestBundle(bundle)}
              />
            ))}
          </div>
        </section>
      ) : null}

      {panierBundles.length > 0 ? (
        <section>
          <PortalPlacerSectionHead
            title="Paniers crypto"
            desc="Des expositions thématiques rééquilibrées chaque mois."
          />
          <div className="placer-grid placer-grid--2">
            {panierBundles.map((bundle) => (
              <PortalPlacerBasketCard
                key={bundle.id}
                bundle={bundle}
                onInvest={() => setInvestBundle(bundle)}
              />
            ))}
          </div>
        </section>
      ) : null}

      {investBundle ? (
        <PortalBundleInvestDialog
          bundle={investBundle}
          open
          onOpenChange={(open) => {
            if (!open) setInvestBundle(null)
          }}
        />
      ) : null}
    </div>
  )
}
