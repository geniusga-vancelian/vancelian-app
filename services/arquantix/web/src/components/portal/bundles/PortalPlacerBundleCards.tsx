'use client'

import Link from 'next/link'
import type { ReactNode } from 'react'

import { appDsCryptoSvgPath } from '@/components/design-system/app/AppProductBasketCard'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { normalizeCryptoBaseTicker, resolveCryptoAvatarSources } from '@/lib/portal/cryptoInstrumentAssets'
import { formatChangePctIndicator } from '@/lib/portal/marketsFormat'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { portalCryptoBundleProductRoute } from '@/lib/portal/portalRouting'

export function isPlacerCoffreBundle(bundle: PortalCryptoBundle): boolean {
  const code = bundle.code.toLowerCase()
  return (
    code.includes('flex') ||
    code.includes('avenir') ||
    code.includes('future') ||
    code.includes('coffre')
  )
}

export function CoffreVaultIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="3" y="6" width="18" height="14" rx="2" />
      <path d="M3 10h18M8 16h3" />
    </svg>
  )
}

export function HorizonVaultIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  )
}

export function BasketCategoryIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="8" cy="9" r="5" />
      <circle cx="16" cy="15" r="5" />
    </svg>
  )
}

export function resolveBundlePhoto(bundle: PortalCryptoBundle): string {
  if (bundle.imageUrl?.trim()) return bundle.imageUrl.trim()
  const code = bundle.code.toLowerCase()
  if (code.includes('flex')) return '/app-ds/assets/photos/coffre-flex.png'
  if (code.includes('avenir') || code.includes('future')) {
    return '/app-ds/assets/photos/coffre-avenir.png'
  }
  return '/app-ds/assets/photos/panier-crypto.png'
}

export function resolveCurrencyIcon(symbol: string): string {
  const key = symbol.toLowerCase()
  if (key === 'usdc') return '/app-ds/assets/crypto/usdc.svg'
  if (key === 'eurc') return '/app-ds/assets/crypto/eurc.svg'
  return appDsCryptoSvgPath(symbol) ?? '/app-ds/assets/crypto/usdc.svg'
}

export function resolveBundleCurrency(bundle: PortalCryptoBundle): string {
  return (
    bundle.entryAssetDefault?.trim().toUpperCase() ??
    bundle.entryAssetsAllowed[0]?.trim().toUpperCase() ??
    'USDC'
  )
}

export function formatBundleCardPerf(bundle: PortalCryptoBundle): string {
  if (bundle.performance1d != null && Number.isFinite(bundle.performance1d)) {
    const positive = bundle.performance1d >= 0
    const formatted = formatChangePctIndicator(bundle.performance1d)
    return `${positive ? '+' : '−'} ${formatted} (24h)`
  }
  if (bundle.riskLabel?.trim()) return bundle.riskLabel.trim()
  return '—'
}

function resolveCryptoStackIcon(ticker: string): string {
  return appDsCryptoSvgPath(ticker) ?? resolveCryptoAvatarSources(ticker)[0] ?? ''
}

export function BundleCryptoStackChip({
  tickers,
  maxVisible = 4,
}: {
  tickers: string[]
  maxVisible?: number
}) {
  const unique = [...new Set(tickers.map((ticker) => normalizeCryptoBaseTicker(ticker)).filter(Boolean))]
  const visible = unique.slice(0, maxVisible)
  const more = Math.max(0, unique.length - visible.length)
  if (visible.length === 0) return null

  return (
    <span className="o-chip o-chip--stack">
      {visible.map((ticker) => {
        const src = resolveCryptoStackIcon(ticker)
        return (
          <span key={ticker} className="o-chip__a">
            {src ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={src} alt="" />
            ) : null}
          </span>
        )
      })}
      {more > 0 ? <span className="o-chip__more">+{more}</span> : null}
    </span>
  )
}

export function PortalPlacerSectionHead({
  title,
  desc,
  action,
}: {
  title: string
  desc?: string
  action?: ReactNode
}) {
  return (
    <section className="sec sec--lg">
      <header className="sec__head">
        <h2 className="sec__title">{title}</h2>
        {action ? <div className="sec__actions">{action}</div> : null}
      </header>
      {desc ? <p className="sec__desc">{desc}</p> : null}
    </section>
  )
}

export function PortalPlacerSeeAll({ href, children }: { href?: string; children: ReactNode }) {
  const inner = (
    <>
      {children}
      <KalaiIcon name="chevron-right" size={16} className="text-current" aria-hidden />
    </>
  )
  if (href) {
    return (
      <Link href={href} className="sec__more no-underline">
        {inner}
      </Link>
    )
  }
  return (
    <button type="button" className="sec__more">
      {inner}
    </button>
  )
}

function BundleCardBody({
  title,
  description,
  onInvest,
  onWithdraw,
}: {
  title: string
  description: string
  onInvest: () => void
  onWithdraw?: () => void
}) {
  return (
    <div className="offer__body">
      <div className="offer__text">
        <h3 className="offer__title">{title}</h3>
        {description.trim() ? (
          <p className="offer__desc offer__desc--clamp-3">{description}</p>
        ) : null}
      </div>
      <div className="offer__ctas">
        <button
          type="button"
          className="btn btn--primary offer__cta"
          onClick={(event) => {
            event.preventDefault()
            event.stopPropagation()
            onInvest()
          }}
        >
          Invest
        </button>
        {onWithdraw ? (
          <button
            type="button"
            className="btn btn--secondary offer__cta"
            onClick={(event) => {
              event.preventDefault()
              event.stopPropagation()
              onWithdraw()
            }}
          >
            Withdraw
          </button>
        ) : null}
      </div>
    </div>
  )
}

/** Vault catalogue card — handoff CoffreCard (chips on media). */
export function PortalPlacerBundleCoffreCard({
  bundle,
  onInvest,
}: {
  bundle: PortalCryptoBundle
  onInvest: () => void
}) {
  const href = portalCryptoBundleProductRoute(bundle.code, { back: 'invest' })
  const categoryIcon = bundle.code.toLowerCase().includes('avenir') ? 'horizon' : 'vault'
  const currency = resolveBundleCurrency(bundle)
  const perf = formatBundleCardPerf(bundle)

  return (
    <PortalNavLink href={href} className="offer offer--link no-underline">
      <div className="offer__media">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="offer__img" src={resolveBundlePhoto(bundle)} alt="" />
        <span className="offer__cat">
          {categoryIcon === 'horizon' ? <HorizonVaultIcon /> : <CoffreVaultIcon />}
          Vault
        </span>
        <div className="offer__chips">
          <span className="o-chip o-chip--perf">{perf}</span>
          <span className="o-chip o-chip--liq">—</span>
          <span className="o-chip o-chip--cur">
            <span className="o-chip__a">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={resolveCurrencyIcon(currency)} alt="" />
            </span>
            {currency}
          </span>
        </div>
      </div>
      <BundleCardBody title={bundle.title} description={bundle.description} onInvest={onInvest} />
    </PortalNavLink>
  )
}

/** Crypto basket catalogue card — handoff BasketCard (perf + stacked avatars). */
export function PortalPlacerBasketCard({
  bundle,
  onInvest,
}: {
  bundle: PortalCryptoBundle
  onInvest: () => void
}) {
  const href = portalCryptoBundleProductRoute(bundle.code, { back: 'invest' })
  const perf = formatBundleCardPerf(bundle)

  return (
    <PortalNavLink href={href} className="offer offer--link no-underline">
      <div className="offer__media">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="offer__img" src={resolveBundlePhoto(bundle)} alt="" />
        <span className="offer__cat">
          <BasketCategoryIcon />
          Crypto basket
        </span>
        <div className="offer__chips">
          <span className="o-chip o-chip--perf">{perf}</span>
          <BundleCryptoStackChip tickers={bundle.allocationTickers} />
        </div>
      </div>
      <BundleCardBody title={bundle.title} description={bundle.description} onInvest={onInvest} />
    </PortalNavLink>
  )
}

/** DeFi vault card (Morpho / Ledgity) — keeps metrics on the hero. */
export function PortalPlacerCoffreCard({
  title,
  description,
  photo,
  perf,
  liquidity,
  currency,
  currencyIcon,
  categoryIcon,
  href,
  onInvest,
  onWithdraw,
}: {
  title: string
  description: string
  photo: string
  perf: string
  liquidity: string
  currency: string
  currencyIcon: string
  categoryIcon: 'vault' | 'horizon'
  href?: string
  onInvest?: () => void
  onWithdraw?: () => void
}) {
  const inner = (
    <>
      <div className="offer__media">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="offer__img" src={photo} alt="" />
        <span className="offer__cat">
          {categoryIcon === 'horizon' ? <HorizonVaultIcon /> : <CoffreVaultIcon />}
          Vault
        </span>
        <div className="offer__chips">
          <span className="o-chip o-chip--perf">{perf}</span>
          <span className="o-chip o-chip--liq">{liquidity}</span>
          <span className="o-chip o-chip--cur">
            <span className="o-chip__a">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={currencyIcon} alt="" />
            </span>
            {currency}
          </span>
        </div>
      </div>
      <BundleCardBody
        title={title}
        description={description}
        onInvest={() => onInvest?.()}
        onWithdraw={onWithdraw}
      />
    </>
  )

  if (href) {
    return (
      <PortalNavLink href={href} className="offer offer--link no-underline">
        {inner}
      </PortalNavLink>
    )
  }

  return <article className="offer offer--link">{inner}</article>
}
