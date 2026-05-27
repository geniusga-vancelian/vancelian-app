'use client'

import { useState } from 'react'

import { AppNewsDeck } from '@/components/design-system/app/AppNewsDeck'
import {
  AppProductBasketCard,
  buildProductBasketStackFromTickers,
} from '@/components/design-system/app/AppProductBasketCard'
import { PortalBundleInvestDialog } from '@/components/portal/bundles/PortalBundleInvestDialog'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { formatChangePctIndicator } from '@/lib/portal/marketsFormat'
import { portalCryptoBundleProductRoute } from '@/lib/portal/portalRouting'

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
  const stack = buildProductBasketStackFromTickers(
    bundle.allocationTickers.length > 0 ? bundle.allocationTickers : [],
  )

  const detailHref = portalCryptoBundleProductRoute(bundle.code)

  return (
    <PortalNavLink
      href={detailHref}
      className="block text-inherit no-underline"
    >
      <AppProductBasketCard
        className="h-full w-full max-w-none"
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
        onCtaClick={(event) => {
          event.preventDefault()
          event.stopPropagation()
          onInvest(bundle)
        }}
      />
    </PortalNavLink>
  )
}

export function PortalCryptoBundlesSection({ bundles }: Props) {
  const [investBundle, setInvestBundle] = useState<PortalCryptoBundle | null>(null)

  if (bundles.length === 0) return null

  return (
    <section className="flex w-full flex-col gap-4">
      <PortalSectionHeading title="Crypto Bundles" />
      <AppNewsDeck>
        {bundles.map((bundle) => (
          <BundleCard key={bundle.id} bundle={bundle} onInvest={setInvestBundle} />
        ))}
      </AppNewsDeck>
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
