import type { PortalCryptoMarketStat } from '@/components/portal/wallet/PortalCryptoMarketStatsGrid'
import { formatCryptoPrice, formatChangePct } from '@/lib/portal/marketsFormat'

export type PortalCryptoPositionMarketQuote = {
  priceUsd?: number
  priceEur?: number
  change24hPct?: number
  volume24hUsd?: number
  marketCapUsd?: number
}

/** Compact USD label — handoff Position.html (e.g. « 182 B$ », « 14 B$ »). */
export function formatCompactUsd(value: number | undefined | null): string {
  if (value == null || !Number.isFinite(value) || value <= 0) return '—'
  const abs = Math.abs(value)
  if (abs >= 1e12) return `$${(value / 1e12).toFixed(1)}T`
  if (abs >= 1e9) return `$${Math.round(value / 1e9)}B`
  if (abs >= 1e6) return `$${(value / 1e6).toFixed(1)}M`
  return formatCryptoPrice(value, 'USD')
}

function changeTone(pct: number | undefined): 'up' | 'down' | undefined {
  if (pct == null || Number.isNaN(pct) || Math.abs(pct) <= 0.005) return undefined
  return pct > 0 ? 'up' : 'down'
}

/** Market grid — handoff Position.html kind=crypto (`.pos-stats`). */
export function buildCryptoPositionMarketStats(args: {
  ticker: string
  currency: string
  livePrice?: number
  change24hPct?: number
  quote?: PortalCryptoPositionMarketQuote | null
}): PortalCryptoMarketStat[] {
  const { ticker, currency, livePrice, change24hPct, quote } = args
  const priceCurrency = currency === 'USD' ? 'USD' : 'EUR'
  const resolvedPrice =
    livePrice ??
    (priceCurrency === 'EUR' ? quote?.priceEur : quote?.priceUsd) ??
    quote?.priceUsd

  const changePct = change24hPct ?? quote?.change24hPct ?? 0
  const changeLabel = formatChangePct(changePct)

  return [
    {
      key: `${ticker} price`,
      value:
        resolvedPrice != null && resolvedPrice > 0
          ? formatCryptoPrice(resolvedPrice, priceCurrency)
          : '—',
    },
    {
      key: 'Market cap',
      value: formatCompactUsd(quote?.marketCapUsd),
    },
    {
      key: '24h volume',
      value: formatCompactUsd(quote?.volume24hUsd),
    },
    {
      key: '24h change',
      value: changeLabel,
      tone: changeTone(changePct),
    },
  ]
}

export function parseCryptoPositionMarketQuote(
  row: Record<string, unknown> | null | undefined,
): PortalCryptoPositionMarketQuote | null {
  if (!row) return null

  const toNum = (value: unknown): number | undefined => {
    if (value == null) return undefined
    const parsed = Number(String(value).replace(',', '.'))
    return Number.isFinite(parsed) ? parsed : undefined
  }

  return {
    priceUsd: toNum(row.price),
    priceEur: toNum(row.price_eur ?? row.priceEur),
    change24hPct: toNum(row.change_24h_pct ?? row.change24h_pct ?? row.change24hPct),
    volume24hUsd: toNum(row.volume_24h ?? row.volume24h),
    marketCapUsd: toNum(row.market_cap ?? row.marketCap ?? row.market_cap_usd),
  }
}
