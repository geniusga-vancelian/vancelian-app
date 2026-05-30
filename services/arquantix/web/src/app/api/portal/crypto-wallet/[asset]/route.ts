import { NextRequest, NextResponse } from 'next/server'
import type { PortalChain } from '@/config/portalChains'
import { buildBackendUrl } from '@/lib/backend'
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
import { assetToMarketProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import { mapWidgetNewsItems } from '@/lib/portal/marketsFormat'
import {
  maybeApplyLombardWalletOverlay,
  resolveLombardOverlayWalletAddress,
  resolvePortalChainFromSearchParams,
} from '@/lib/portal/lombard/resolveLombardWalletOverlayForApi'
import { fetchLombardBorrowWalletTransactions } from '@/lib/portal/lombard/lombardWalletTransactions'
import { appendPortalScopeQuery } from '@/lib/portal/portalScopeQuery'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
import type { PortalWalletScope } from '@/lib/portal/portalWalletScopeTypes'

async function fetchUpstreamJson(path: string) {
  const res = await portalUpstreamFetch(path, { signal: AbortSignal.timeout(15000) })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

async function fetchBackendJson(path: string) {
  const res = await fetch(buildBackendUrl(path), {
    cache: 'no-store',
    signal: AbortSignal.timeout(15000),
  })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

async function fetchJson(url: string) {
  const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(15000) })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

function resolvePortalChain(request: NextRequest): PortalChain {
  return resolvePortalChainFromSearchParams(request.nextUrl.searchParams.get('portal_chain'))
}

function resolveWalletScope(request: NextRequest, chain: PortalChain): PortalWalletScope | null {
  const walletAddress = request.nextUrl.searchParams.get('wallet_address')?.trim()
  if (!walletAddress) return null
  return {
    id: `scope:${walletAddress}`,
    kind: 'privy_embedded',
    label: 'Privy',
    shortLabel: 'Privy',
    address: walletAddress,
    chainType: chain === 'solana' ? 'solana' : 'evm',
  }
}

/** Détail position crypto — aligné hub wallet (Privy + scope navbar). */
export async function GET(
  request: NextRequest,
  { params }: { params: { asset: string } },
) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const personId = await requirePortalPersonId()
  if (personId instanceof NextResponse) return personId

  const asset = (params.asset ?? '').trim().toUpperCase()
  if (!asset) {
    return NextResponse.json({ error: 'invalid_asset' }, { status: 400 })
  }

  const portalChain = resolvePortalChain(request)
  const walletScope = resolveWalletScope(request, portalChain)
  const providerSymbol = assetToMarketProviderSymbol(asset)
  const assetSlug = asset.toLowerCase()
  const bffOrigin = resolvePortalBffOrigin(request.nextUrl.origin)
  const scopedDetailUrl = appendPortalScopeQuery(
    `/api/app/crypto-positions/${encodeURIComponent(asset)}`,
    portalChain,
    walletScope,
  )

  const [detailRes, directRes, txRes, privyDepRes, historyRes, bootstrapRes, marketRes, blogWidgetRes] =
    await Promise.all([
      fetchUpstreamJson(scopedDetailUrl),
      fetchUpstreamJson('/api/app/crypto-positions/direct'),
      fetchUpstreamJson(
        `/api/app/crypto-positions/${encodeURIComponent(asset)}/transactions`,
      ),
      fetchUpstreamJson(
        `/api/app/privy-wallet/deposits?asset=${encodeURIComponent(asset)}&limit=50`,
      ),
      fetchUpstreamJson(
        `/api/app/wallet/history?period=ALL&asset=${encodeURIComponent(asset)}&mode=performance_value`,
      ),
      fetchUpstreamJson('/api/app/bootstrap'),
      fetchBackendJson(
        `/api/market-data/market-summary?symbols=${encodeURIComponent(providerSymbol)}`,
      ),
      fetchJson(
        `${bffOrigin}/api/mobile/flutter/widgets/blog-a-la-une?locale=${PORTAL_CONTENT_LOCALE}&assetSlug=${encodeURIComponent(assetSlug)}`,
      ),
    ])

  const currency =
    bootstrapRes.ok && bootstrapRes.data && typeof bootstrapRes.data === 'object'
      ? String(
          (bootstrapRes.data as Record<string, unknown>).client &&
            typeof (bootstrapRes.data as Record<string, unknown>).client === 'object'
            ? ((bootstrapRes.data as Record<string, unknown>).client as Record<string, unknown>)
                .reference_currency ?? 'EUR'
            : 'EUR',
        )
          .trim()
          .toUpperCase()
      : 'EUR'

  let scopedPosition = undefined
  if (directRes.ok && directRes.data) {
    let directSummary = parseSelfTradingCryptoPositionsPayload(directRes.data)
    try {
      directSummary = await maybeApplyLombardWalletOverlay({
        personId,
        portalChain,
        walletAddress: await resolveLombardOverlayWalletAddress({
          request,
          walletFromQuery: walletScope?.address ?? null,
        }),
        summary: directSummary,
      })
    } catch (error) {
      console.warn('[api/portal/crypto-wallet/[asset] GET] Lombard overlay skipped:', error)
    }
    scopedPosition = resolveScopedPrivyPositionForAsset(
      directSummary,
      asset,
      portalChain,
      walletScope,
    )
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

  if (!detail) {
    return NextResponse.json({ error: 'not_found' }, { status: 404 })
  }

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
      if (rawLogo != null && String(rawLogo).trim()) {
        logoUrl = String(rawLogo).trim()
      }
    }
  }

  const blogFeed = (blogWidgetRes.data as { feeds?: Record<string, unknown> })?.feeds?.[
    'blog-a-la-une'
  ]
  const news = mapWidgetNewsItems(blogFeed, bffOrigin).slice(0, 5)

  let transactions = mergeCryptoWalletTransactions(
    txRes.ok ? txRes.data : null,
    privyDepRes.ok ? privyDepRes.data : null,
  )

  if (asset === 'USDC') {
    try {
      const walletAddress = await resolveLombardOverlayWalletAddress({
        request,
        walletFromQuery: walletScope?.address ?? null,
      })
      if (walletAddress) {
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
      }
    } catch (error) {
      console.warn('[api/portal/crypto-wallet/[asset] GET] Lombard borrow tx merge skipped:', error)
    }
  }

  return NextResponse.json({
    currency,
    detail,
    transactions,
    historyPoints: historyRes.ok ? parseWalletHistoryPoints(historyRes.data) : [],
    performance: historyRes.ok ? parseWalletHistoryPerformance(historyRes.data) : null,
    change24hPct: change24hPct ?? marketQuote?.change24hPct,
    providerSymbol,
    logoUrl,
    marketQuote,
    news,
    partial: !detailRes.ok || !txRes.ok || !privyDepRes.ok || !historyRes.ok || !directRes.ok,
  })
}
