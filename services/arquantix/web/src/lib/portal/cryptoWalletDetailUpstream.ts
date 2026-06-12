import type { PortalChain } from '@/config/portalChains'
import {
  alignCryptoWalletDetailWithScopedPosition,
  buildCryptoWalletDetailFromScopedPosition,
  extractUpstreamDetailPayload,
  mergeCryptoWalletTransactions,
  mergeLombardBorrowWalletTransactions,
  parseCryptoWalletDetail,
  parseSelfTradingCryptoPositionsPayload,
  parseWalletHistoryPerformance,
  parseWalletHistoryPoints,
  resolveScopedPrivyPositionForAsset,
} from '@/lib/portal/cryptoWalletFormat'
import { parseCryptoPositionMarketQuote } from '@/lib/portal/cryptoPositionDetailFormat'
import { resolveDashboardReferenceCurrency } from '@/lib/portal/dashboardMerge'
import { assetToMarketProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import { mapWidgetNewsItems } from '@/lib/portal/marketsFormat'
import { maybeApplyLombardWalletOverlay } from '@/lib/portal/lombard/resolveLombardWalletOverlayForApi'
import { fetchLombardBorrowWalletTransactions } from '@/lib/portal/lombard/lombardWalletTransactions'
import { appendPortalScopeQuery } from '@/lib/portal/portalScopeQuery'
import {
  fetchPortalBackendJsonSafe,
  fetchPortalUpstreamJsonSafe,
  PORTAL_UPSTREAM_DEFAULT_TIMEOUT_MS,
  PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS,
} from '@/lib/portal/portalUpstream'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import type { PortalWalletScope } from '@/lib/portal/portalWalletScopeTypes'
import type {
  PortalCryptoWalletDetailActivityPayload,
  PortalCryptoWalletDetailCorePayload,
  PortalCryptoWalletDetailNewsPayload,
} from '@/lib/portal/cryptoWalletTypes'

export type CryptoWalletDetailScopeArgs = {
  asset: string
  personId: string
  portalChain: PortalChain
  walletScope: PortalWalletScope | null
  walletAddress: string | null
}

async function fetchJsonSafe(url: string) {
  try {
    const res = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(PORTAL_UPSTREAM_DEFAULT_TIMEOUT_MS),
    })
    const data = await res.json().catch(() => null)
    return { ok: res.ok, data }
  } catch {
    return { ok: false, data: null }
  }
}

/**
 * Section core : position détaillée alignée scope + cotation marché.
 * Retourne `null` (→ 404) si aucune position détaillée n'est disponible.
 */
export async function loadCryptoWalletDetailCore(
  args: CryptoWalletDetailScopeArgs,
): Promise<PortalCryptoWalletDetailCorePayload | null> {
  const { asset, personId, portalChain, walletScope, walletAddress } = args
  const providerSymbol = assetToMarketProviderSymbol(asset)
  const scopedDetailUrl = appendPortalScopeQuery(
    `/api/app/crypto-positions/${encodeURIComponent(asset)}`,
    portalChain,
    walletScope,
  )

  const [detailRes, directRes, bootstrapRes, marketRes] = await Promise.all([
    fetchPortalUpstreamJsonSafe(scopedDetailUrl, { timeoutMs: PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS }),
    fetchPortalUpstreamJsonSafe('/api/app/crypto-positions/direct', {
      timeoutMs: PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS,
    }),
    fetchPortalUpstreamJsonSafe('/api/app/bootstrap'),
    fetchPortalBackendJsonSafe(
      `/api/market-data/market-summary?symbols=${encodeURIComponent(providerSymbol)}`,
    ),
  ])

  const currency = resolveDashboardReferenceCurrency(bootstrapRes.ok ? bootstrapRes.data : null)

  let scopedPosition = undefined
  if (directRes.ok && directRes.data) {
    let directSummary = parseSelfTradingCryptoPositionsPayload(directRes.data)
    try {
      directSummary = await maybeApplyLombardWalletOverlay({
        personId,
        portalChain,
        walletAddress,
        summary: directSummary,
      })
    } catch (error) {
      console.warn('[cryptoWalletDetailCore] Lombard overlay skipped:', error)
    }
    scopedPosition = resolveScopedPrivyPositionForAsset(directSummary, asset, portalChain, walletScope)
  }

  const upstreamDetail = detailRes.ok
    ? parseCryptoWalletDetail(extractUpstreamDetailPayload(detailRes.data))
    : null

  let detail = upstreamDetail
  if (scopedPosition) {
    detail = upstreamDetail
      ? alignCryptoWalletDetailWithScopedPosition(upstreamDetail, scopedPosition)
      : buildCryptoWalletDetailFromScopedPosition(scopedPosition)
  }

  if (!detail) return null

  let change24hPct: number | undefined
  let logoUrl: string | null = null
  let marketQuote = null as ReturnType<typeof parseCryptoPositionMarketQuote>
  if (marketRes.ok && marketRes.data) {
    const summaries =
      (marketRes.data as { summaries?: unknown })?.summaries ??
      (Array.isArray(marketRes.data) ? marketRes.data : null)
    const first = Array.isArray(summaries) ? summaries[0] : null
    if (first && typeof first === 'object') {
      const row = first as Record<string, unknown>
      marketQuote = parseCryptoPositionMarketQuote(row)
      const raw = row.change_24h_pct ?? row.change24h_pct ?? row.change24hPct
      if (raw != null) change24hPct = Number(String(raw).replace('+', ''))
      const rawLogo = row.logo_url ?? row.logoUrl
      if (rawLogo != null && String(rawLogo).trim()) logoUrl = String(rawLogo).trim()
    }
  }

  return {
    currency,
    detail,
    change24hPct: change24hPct ?? marketQuote?.change24hPct,
    providerSymbol,
    logoUrl,
    marketQuote,
    partial: !detailRes.ok || !directRes.ok,
  }
}

/** Section activity : transactions (+ borrow Lombard USDC) + courbe perf. */
export async function loadCryptoWalletDetailActivity(
  args: CryptoWalletDetailScopeArgs,
): Promise<PortalCryptoWalletDetailActivityPayload> {
  const { asset, personId, walletAddress } = args

  const [txRes, privyDepRes, historyRes] = await Promise.all([
    fetchPortalUpstreamJsonSafe(
      `/api/app/crypto-positions/${encodeURIComponent(asset)}/transactions`,
      { timeoutMs: PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS },
    ),
    fetchPortalUpstreamJsonSafe(
      `/api/app/privy-wallet/deposits?asset=${encodeURIComponent(asset)}&limit=50`,
    ),
    fetchPortalUpstreamJsonSafe(
      `/api/app/wallet/history?period=ALL&asset=${encodeURIComponent(asset)}&mode=performance_value`,
      { timeoutMs: PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS },
    ),
  ])

  let transactions = mergeCryptoWalletTransactions(
    txRes.ok ? txRes.data : null,
    privyDepRes.ok ? privyDepRes.data : null,
  )

  if (asset === 'USDC' && walletAddress) {
    try {
      const lombardBorrow = await fetchLombardBorrowWalletTransactions({
        personId,
        walletAddress,
        asset,
      })
      transactions = mergeLombardBorrowWalletTransactions(
        transactions,
        lombardBorrow.transactions,
        lombardBorrow.hiddenPrivyKeys,
      )
    } catch (error) {
      console.warn('[cryptoWalletDetailActivity] Lombard borrow tx merge skipped:', error)
    }
  }

  return {
    transactions,
    historyPoints: historyRes.ok ? parseWalletHistoryPoints(historyRes.data) : [],
    performance: historyRes.ok ? parseWalletHistoryPerformance(historyRes.data) : null,
    partial: !txRes.ok || !privyDepRes.ok || !historyRes.ok,
  }
}

/** Section news : actualités liées à l'asset (widget blog). */
export async function loadCryptoWalletDetailNews(
  asset: string,
  bffOrigin: string,
  locale: string = PORTAL_CONTENT_LOCALE,
): Promise<PortalCryptoWalletDetailNewsPayload> {
  const assetSlug = asset.toLowerCase()
  const res = await fetchJsonSafe(
    `${bffOrigin}/api/mobile/flutter/widgets/blog-a-la-une?locale=${locale}&assetSlug=${encodeURIComponent(assetSlug)}`,
  )
  const blogFeed = (res.data as { feeds?: Record<string, unknown> })?.feeds?.['blog-a-la-une']
  return {
    news: mapWidgetNewsItems(blogFeed, bffOrigin).slice(0, 5),
    partial: !res.ok,
  }
}
