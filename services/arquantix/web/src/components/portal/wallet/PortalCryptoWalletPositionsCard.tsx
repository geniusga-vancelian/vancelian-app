'use client'

import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import {
  formatCryptoMoney,
  resolveCategoryCryptoRowSubtitle,
} from '@/lib/portal/cryptoWalletFormat'
import {
  cryptoBrandColor,
  normalizeCryptoBaseTicker,
  resolveCryptoAvatarSources,
} from '@/lib/portal/cryptoInstrumentAssets'
import { cryptoPositionHeaderTitle, tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import type { PortalCryptoWalletRow } from '@/lib/portal/cryptoWalletTypes'
import {
  portalCryptoWalletAssetRoute,
  portalCryptoWalletBundleRoute,
} from '@/lib/portal/portalRouting'

type Props = {
  rows: PortalCryptoWalletRow[]
  currency: string
  count?: number
  emptyMessage?: string
  footerHint?: string
}

function resolveCoinIconUrl(ticker: string, apiLogoUrl?: string | null): string {
  const sources = resolveCryptoAvatarSources(ticker, apiLogoUrl)
  if (sources[0]) return sources[0]
  const base = normalizeCryptoBaseTicker(ticker).toLowerCase()
  return `/app-ds/crypto/${base}.svg`
}

function CategoryPositionMedia({ row }: { row: PortalCryptoWalletRow }) {
  if (row.kind === 'bundle') {
    const tickers = (row.bundle.positions ?? [])
      .map((position) => position.asset.trim().toUpperCase())
      .filter(Boolean)
    const visible = tickers.slice(0, 3)
    const extra = tickers.length - visible.length

    if (visible.length === 0) {
      return (
        <span className="cat-pos__media cat-pos__media--mono" style={{ background: 'var(--v-fg)' }}>
          P
        </span>
      )
    }

    return (
      <span className="cat-pos__media cat-pos__media--stack" aria-hidden="true">
        {visible.map((ticker, index) => (
          <span
            key={ticker}
            className="cat-pos__stack-item"
            style={{ marginLeft: index === 0 ? 0 : -10, zIndex: 10 - index }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={resolveCoinIconUrl(ticker)} alt="" />
          </span>
        ))}
        {extra > 0 ? (
          <span className="cat-pos__stack-more" style={{ marginLeft: -10, zIndex: 5 }}>
            +{extra}
          </span>
        ) : null}
      </span>
    )
  }

  const { position } = row
  const ticker = position.asset
  const iconUrl = resolveCoinIconUrl(
    ticker,
    position.logoUrl ?? position.providerSymbol ?? tickerToProviderSymbol(ticker),
  )
  const brand = cryptoBrandColor(normalizeCryptoBaseTicker(ticker))

  return (
    <span
      className="cat-pos__media cat-pos__media--coin"
      style={{ background: brand }}
      aria-hidden="true"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={iconUrl} alt="" />
    </span>
  )
}

function CategoryPositionRow({
  row,
  currency,
}: {
  row: PortalCryptoWalletRow
  currency: string
}) {
  const href =
    row.kind === 'bundle'
      ? portalCryptoWalletBundleRoute(row.bundle.portfolioId)
      : portalCryptoWalletAssetRoute(row.position.asset)

  const title =
    row.kind === 'bundle'
      ? row.bundle.portfolioName
      : cryptoPositionHeaderTitle(row.position.asset, row.position.name)

  const amount =
    row.kind === 'bundle'
      ? formatCryptoMoney(
          row.value,
          currency,
        )
      : formatCryptoMoney(
          currency === 'USD'
            ? row.position.estimatedValueUsd ?? row.position.estimatedValueEur
            : row.position.estimatedValueEur ?? row.position.estimatedValueUsd,
          currency,
        )

  const subtitle = resolveCategoryCryptoRowSubtitle(row)

  return (
    <PortalNavLink href={href} className="cat-pos no-underline">
      <CategoryPositionMedia row={row} />
      <span className="cat-pos__body">
        <span className="cat-pos__title">{title}</span>
        <span className="cat-pos__sub">{subtitle}</span>
      </span>
      <span className="cat-pos__amt">{amount}</span>
      <KalaiIcon name="chevron-right" size={16} className="cat-pos__chv" aria-hidden />
    </PortalNavLink>
  )
}

/** Liste positions crypto — handoff `.cat-positions` (Compte.html?id=cryptos). */
export function PortalCryptoWalletPositionsCard({
  rows,
  currency,
  count,
  emptyMessage = 'No crypto positions yet',
  footerHint,
}: Props) {
  const resolvedCount = count ?? rows.length

  if (rows.length === 0) {
    return (
      <section className="flex w-full flex-col gap-3">
        <AppSectionHeader title="My positions" size="lg" />
        <p className="m-0 rounded-v-card border border-v-fg-10 bg-v-card px-6 py-10 text-center font-ui text-[15px] text-v-fg-muted">
          {emptyMessage}
        </p>
      </section>
    )
  }

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader
        title="My positions"
        size="lg"
        count={resolvedCount > 0 ? resolvedCount : undefined}
      />
      <div className="v-card cat-positions">
        <div className="cat-positions__list">
          {rows.map((row, index) => (
            <div key={row.kind === 'bundle' ? `bundle-${row.bundle.portfolioId}` : `pos-${row.position.asset}`}>
              <CategoryPositionRow row={row} currency={currency} />
              {index < rows.length - 1 ? <hr className="cat-positions__sep" /> : null}
            </div>
          ))}
        </div>
        {footerHint ? (
          <div className="cat-positions__foot">
            <KalaiIcon name="info" size={16} aria-hidden />
            <span>{footerHint}</span>
          </div>
        ) : null}
      </div>
    </section>
  )
}
