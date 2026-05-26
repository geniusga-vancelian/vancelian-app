'use client'

import type { ReactNode } from 'react'
import { AppButton } from '@/components/design-system/app/AppButton'
import { normalizeCryptoBaseTicker } from '@/lib/portal/cryptoInstrumentAssets'
import { cn } from '@/lib/utils'

export type AppProductBasketStackAsset = {
  src: string
  alt?: string
}

export type AppProductBasketCardProps = {
  heroImageUrl?: string | null
  heroTitle: string
  heroDescription?: string
  stackAssets?: AppProductBasketStackAsset[]
  stackMoreCount?: number
  footName: string
  performanceLabel: string
  performancePositive?: boolean | null
  footIcon?: ReactNode
  ctaLabel?: string
  onCtaClick?: () => void
  ctaDisabled?: boolean
  className?: string
}

function TrendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M4 16l5-6 4 4 7-9" />
      <path d="M14 5h6v6" />
    </svg>
  )
}

function StackRow({
  assets,
  moreCount,
}: {
  assets: AppProductBasketStackAsset[]
  moreCount?: number
}) {
  if (assets.length === 0 && !moreCount) return null

  return (
    <div className="prod__stack" aria-hidden>
      {assets.map((asset, index) => (
        <span key={`${asset.src}-${index}`} className="a">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={asset.src} alt={asset.alt ?? ''} />
        </span>
      ))}
      {moreCount && moreCount > 0 ? <span className="a a--more">+{moreCount}</span> : null}
    </div>
  )
}

/** Carte produit marketing panier / coffre — DS `76-card-product-basket`. */
export function AppProductBasketCard({
  heroImageUrl,
  heroTitle,
  heroDescription,
  stackAssets = [],
  stackMoreCount,
  footName,
  performanceLabel,
  performancePositive = true,
  footIcon,
  ctaLabel = 'Investir',
  onCtaClick,
  ctaDisabled,
  className,
}: AppProductBasketCardProps) {
  return (
    <article className={cn('prod', className)}>
      <div className="prod__hero">
        {heroImageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img className="prod__img" src={heroImageUrl} alt="" />
        ) : null}
        <StackRow assets={stackAssets} moreCount={stackMoreCount} />
        <div className="prod__spacer" />
        <h3 className="prod__title">{heroTitle}</h3>
        {heroDescription ? <p className="prod__desc">{heroDescription}</p> : null}
      </div>
      <div className="prod__foot">
        <div className="prod__thumb">{footIcon ?? <TrendIcon />}</div>
        <div className="prod__meta">
          <div className="prod__name">{footName}</div>
          <div
            className={cn(
              'prod__perf',
              performancePositive === false && 'prod__perf--down',
            )}
          >
            {performanceLabel}
          </div>
        </div>
        <AppButton size="sm" disabled={ctaDisabled} onClick={onCtaClick}>
          {ctaLabel}
        </AppButton>
      </div>
    </article>
  )
}

export function appDsCryptoSvgPath(rawTicker: string): string | null {
  const key = normalizeCryptoBaseTicker(rawTicker).toLowerCase()
  if (!key) return null
  return `/app-ds/crypto/${key}.svg`
}

export function buildProductBasketStackFromTickers(
  tickers: string[],
  maxVisible = 4,
): { assets: AppProductBasketStackAsset[]; moreCount?: number } {
  const unique = [...new Set(tickers.map((t) => normalizeCryptoBaseTicker(t)).filter(Boolean))]
  const visible = unique.slice(0, maxVisible)
  const assets = visible
    .map((ticker) => {
      const src = appDsCryptoSvgPath(ticker)
      return src ? { src, alt: ticker } : null
    })
    .filter((item): item is AppProductBasketStackAsset => item != null)
  const moreCount = unique.length > maxVisible ? unique.length - maxVisible : undefined
  return { assets, moreCount }
}
