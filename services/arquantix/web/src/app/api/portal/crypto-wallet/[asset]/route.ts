import { NextRequest, NextResponse } from 'next/server'
import { DEFAULT_PORTAL_CHAIN, isValidPortalChain, type PortalChain } from '@/config/portalChains'
import { buildBackendUrl } from '@/lib/backend'
import {
  alignCryptoWalletDetailWithScopedPosition,
  buildPrivyWalletPositionsSummary,
  extractUpstreamDetailPayload,
  mergeCryptoWalletTransactions,
  parseCryptoWalletDetail,
  parseWalletHistoryPoints,
  resolveScopedPrivyPositionForAsset,
} from '@/lib/portal/cryptoWalletFormat'
import { tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import { appendPortalScopeQuery } from '@/lib/portal/portalScopeQuery'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
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

function resolvePortalChain(request: NextRequest): PortalChain {
  const raw = request.nextUrl.searchParams.get('portal_chain')?.trim().toLowerCase() ?? ''
  return isValidPortalChain(raw) ? raw : DEFAULT_PORTAL_CHAIN
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

  const asset = (params.asset ?? '').trim().toUpperCase()
  if (!asset) {
    return NextResponse.json({ error: 'invalid_asset' }, { status: 400 })
  }

  const portalChain = resolvePortalChain(request)
  const walletScope = resolveWalletScope(request, portalChain)
  const providerSymbol = tickerToProviderSymbol(asset)
  const scopedDetailUrl = appendPortalScopeQuery(
    `/api/app/crypto-positions/${encodeURIComponent(asset)}`,
    portalChain,
    walletScope,
  )

  const detailRes = await fetchUpstreamJson(scopedDetailUrl)

  if (!detailRes.ok || !detailRes.data) {
    return NextResponse.json({ error: 'detail_unavailable' }, { status: 502 })
  }

  const detailRaw = extractUpstreamDetailPayload(detailRes.data)
  let detail = parseCryptoWalletDetail(detailRaw)
  if (!detail) {
    return NextResponse.json({ error: 'not_found' }, { status: 404 })
  }

  const [txRes, privyDepRes, historyRes, bootstrapRes, marketRes, privyBalancesRes] =
    await Promise.all([
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
      fetchUpstreamJson('/api/app/privy-wallet/balances'),
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

  if (privyBalancesRes.ok && privyBalancesRes.data) {
    const privySummary = buildPrivyWalletPositionsSummary(
      privyBalancesRes.data,
      marketRes.ok ? marketRes.data : null,
      currency,
    )
    const scopedPosition = resolveScopedPrivyPositionForAsset(
      privySummary,
      asset,
      portalChain,
      walletScope,
    )
    detail = alignCryptoWalletDetailWithScopedPosition(detail, scopedPosition)
  }

  let change24hPct: number | undefined
  let logoUrl: string | null = null
  if (marketRes.ok && marketRes.data) {
    const summaries =
      (marketRes.data as { summaries?: unknown })?.summaries ??
      (Array.isArray(marketRes.data) ? marketRes.data : null)
    const first = Array.isArray(summaries) ? summaries[0] : null
    if (first && typeof first === 'object') {
      const row = first as Record<string, unknown>
      const raw = row.change_24h_pct ?? row.change24h_pct ?? row.change24hPct
      if (raw != null) change24hPct = Number(String(raw).replace('+', ''))
      const rawLogo = row.logo_url ?? row.logoUrl
      if (rawLogo != null && String(rawLogo).trim()) {
        logoUrl = String(rawLogo).trim()
      }
    }
  }

  const transactions = mergeCryptoWalletTransactions(
    txRes.ok ? txRes.data : null,
    privyDepRes.ok ? privyDepRes.data : null,
  )

  return NextResponse.json({
    currency,
    detail,
    transactions,
    historyPoints: historyRes.ok ? parseWalletHistoryPoints(historyRes.data) : [],
    change24hPct,
    providerSymbol,
    logoUrl,
    partial: !txRes.ok || !privyDepRes.ok || !historyRes.ok || !privyBalancesRes.ok,
  })
}
