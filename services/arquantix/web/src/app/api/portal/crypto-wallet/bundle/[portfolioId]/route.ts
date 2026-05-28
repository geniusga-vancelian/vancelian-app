import { NextRequest, NextResponse } from 'next/server'
import {
  findMyBundleByPortfolioId,
  parseCryptoWalletTransactions,
  parseMyBundles,
  parseWalletHistoryPoints,
} from '@/lib/portal/cryptoWalletFormat'
import { consolidateSwapTransactions } from '@/lib/portal/cryptoTransactionHistoryFormat'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

async function fetchUpstreamJson(path: string) {
  const res = await portalUpstreamFetch(path, { signal: AbortSignal.timeout(15000) })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

/** Détail bundle wallet — résumé client + historique performance. */
export async function GET(
  _request: NextRequest,
  { params }: { params: { portfolioId: string } },
) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const portfolioId = (params.portfolioId ?? '').trim()
  if (!portfolioId) {
    return NextResponse.json({ error: 'invalid_portfolio_id' }, { status: 400 })
  }

  const [bundlesRes, historyRes, bootstrapRes, txRes] = await Promise.all([
    fetchUpstreamJson('/api/app/bundle/my-bundles'),
    fetchUpstreamJson(
      `/api/app/bundle/${encodeURIComponent(portfolioId)}/history?period=ALL&mode=performance_value`,
    ),
    fetchUpstreamJson('/api/app/bootstrap'),
    fetchUpstreamJson(
      `/api/app/bundle/${encodeURIComponent(portfolioId)}/transactions`,
    ),
  ])

  if (!bundlesRes.ok) {
    return NextResponse.json({ error: 'bundles_unavailable' }, { status: 502 })
  }

  const bundles = parseMyBundles(bundlesRes.data)
  const bundle = findMyBundleByPortfolioId(bundles, portfolioId)
  if (!bundle) {
    return NextResponse.json({ error: 'bundle_not_found' }, { status: 404 })
  }

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

  const historyPoints = historyRes.ok ? parseWalletHistoryPoints(historyRes.data) : []
  const transactions = consolidateSwapTransactions(
    txRes.ok ? parseCryptoWalletTransactions(txRes.data) : [],
  )

  return NextResponse.json({
    currency,
    bundle,
    historyPoints,
    transactions,
    partial: !historyRes.ok || !txRes.ok,
  })
}
