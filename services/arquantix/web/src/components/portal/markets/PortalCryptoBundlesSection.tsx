'use client'

import { useState } from 'react'

import {
  AppProductBasketCard,
  buildProductBasketStackFromTickers,
} from '@/components/design-system/app/AppProductBasketCard'
import { PortalBundleInvestDialog } from '@/components/portal/bundles/PortalBundleInvestDialog'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { formatChangePctIndicator } from '@/lib/portal/marketsFormat'

type Props = {
  bundles: PortalCryptoBundle[]
}

function VaultIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="3" y="6" width="18" height="14" rx="2" />
      <path d="M3 10h18M8 16h3" />
    </svg>
  )
}

function HorizonIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  )
}

function TrendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M4 16l5-6 4 4 7-9" />
      <path d="M14 5h6v6" />
    </svg>
  )
}

function resolveBundleHeroImage(bundle: PortalCryptoBundle): string {
  if (bundle.imageUrl?.trim()) return bundle.imageUrl.trim()
  const code = bundle.code.toLowerCase()
  if (code.includes('flex')) return '/app-ds/assets/photos/coffre-flex.png'
  if (code.includes('avenir') || code.includes('future')) {
    return '/app-ds/assets/photos/coffre-avenir.png'
  }
  return '/app-ds/assets/photos/panier-crypto.png'
}

function resolveBundleFootIcon(bundle: PortalCryptoBundle) {
  const code = bundle.code.toLowerCase()
  if (code.includes('flex')) return <VaultIcon />
  if (code.includes('avenir') || code.includes('future')) return <HorizonIcon />
  return <TrendIcon />
}

function formatBasketPerformance(value: number | null): { label: string; positive: boolean | null } {
  if (value == null) return { label: '—', positive: null }
  const positive = value >= 0
  const formatted = formatChangePctIndicator(value)
  return {
    label: `${positive ? '+' : '−'}${formatted}`,
    positive,
  }
}

function BundleCard({
  bundle,
  onInvest,
}: {
  bundle: PortalCryptoBundle
  onInvest: (bundle: PortalCryptoBundle) => void
}) {
  const perf = formatBasketPerformance(bundle.performance1d)
  const stack =
    bundle.entryAssetsAllowed.length > 0
      ? buildProductBasketStackFromTickers(bundle.entryAssetsAllowed)
      : { assets: [], moreCount: undefined }

  return (
    <AppProductBasketCard
      heroImageUrl={resolveBundleHeroImage(bundle)}
      heroTitle={bundle.title}
      heroDescription={bundle.description || undefined}
      stackAssets={stack.assets}
      stackMoreCount={stack.moreCount}
      footName={bundle.title}
      performanceLabel={perf.label}
      performancePositive={perf.positive}
      footIcon={resolveBundleFootIcon(bundle)}
      ctaLabel="Invest"
      ctaDisabled={!bundle.portfolioId}
      onCtaClick={() => onInvest(bundle)}
    />
  )
}

export function PortalCryptoBundlesSection({ bundles }: Props) {
  const [investBundle, setInvestBundle] = useState<PortalCryptoBundle | null>(null)

  if (bundles.length === 0) return null

  return (
    <section className="flex flex-col gap-4">
      <PortalSectionHeading title="Crypto Bundles" />
      <div className="grid grid-cols-1 justify-items-stretch gap-4 sm:grid-cols-2 xl:justify-items-start">
        {bundles.map((bundle) => (
          <BundleCard key={bundle.id} bundle={bundle} onInvest={setInvestBundle} />
        ))}
      </div>
      {investBundle ? (
        <PortalBundleInvestDialog
          bundle={investBundle}
          open
          onOpenChange={(open) => {
            if (!open) setInvestBundle(null)
          }}
        />
      ) : null}
    </section>
  )
}
