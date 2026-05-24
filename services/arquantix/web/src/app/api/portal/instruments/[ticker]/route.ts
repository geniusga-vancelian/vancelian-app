import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import { getMarketDataPublicBaseUrl } from '@/lib/portal/marketDataPublic'
import {
  instrumentDisplayName,
  normalizeInstrumentTicker,
  tickerToProviderSymbol,
} from '@/lib/portal/instrumentDetailFormat'
import type { PortalInstrumentDetailPayload } from '@/lib/portal/instrumentDetailTypes'
import {
  mapMarketSummaryRow,
  mapWidgetNewsItems,
  mapWidgetResearchItems,
} from '@/lib/portal/marketsFormat'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'

async function fetchJson(url: string) {
  const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(15000) })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

export async function GET(
  request: NextRequest,
  { params }: { params: { ticker: string } },
) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const ticker = normalizeInstrumentTicker(params.ticker ?? '')
  if (!ticker) {
    return NextResponse.json({ error: 'Invalid ticker' }, { status: 400 })
  }

  const symbol = tickerToProviderSymbol(ticker)
  const assetSlug = ticker.toLowerCase()
  const publicOrigin = request.nextUrl.origin
  const bffOrigin = resolvePortalBffOrigin(publicOrigin)
  const marketDataPublicBaseUrl = getMarketDataPublicBaseUrl()

  const [summaryRes, blogWidgetRes, researchWidgetRes] = await Promise.all([
    fetchJson(buildBackendUrl(`/api/market-data/market-summary?symbols=${encodeURIComponent(symbol)}`)),
    fetchJson(
      `${bffOrigin}/api/mobile/flutter/widgets/blog-a-la-une?locale=fr&assetSlug=${encodeURIComponent(assetSlug)}`,
    ),
    fetchJson(
      `${bffOrigin}/api/mobile/flutter/widgets/research-a-la-une?locale=fr&assetSlug=${encodeURIComponent(assetSlug)}`,
    ),
  ])

  const summaries =
    (summaryRes.data as { summaries?: unknown })?.summaries ??
    (Array.isArray(summaryRes.data) ? summaryRes.data : null)
  const summaryRow = Array.isArray(summaries) ? summaries[0] : null
  const mapped = summaryRow
    ? mapMarketSummaryRow(summaryRow as Record<string, unknown>, {
        currency: 'USD',
        logoBaseUrl: marketDataPublicBaseUrl,
      })
    : null

  const blogFeed = (blogWidgetRes.data as { feeds?: Record<string, unknown> })?.feeds?.['blog-a-la-une']
  const researchFeed = (researchWidgetRes.data as { feeds?: Record<string, unknown> })?.feeds?.[
    'research-a-la-une'
  ]

  const rawSummary = summaryRow as Record<string, unknown> | null
  const change24hAbsRaw = rawSummary?.change_24h_abs ?? rawSummary?.change24hAbs
  const change24hAbs =
    typeof change24hAbsRaw === 'number'
      ? change24hAbsRaw
      : Number.parseFloat(String(change24hAbsRaw ?? '')) || null

  const instrumentIdRaw = rawSummary?.instrument_id ?? rawSummary?.instrumentId
  const instrumentId =
    typeof instrumentIdRaw === 'number'
      ? instrumentIdRaw
      : Number.parseInt(String(instrumentIdRaw ?? ''), 10) || null

  const payload: PortalInstrumentDetailPayload = {
    ticker,
    symbol,
    name: mapped?.name ?? instrumentDisplayName(ticker),
    priceUsd: mapped?.priceUsd ?? 0,
    priceLabel: mapped?.priceLabel ?? '—',
    change24hPct: mapped?.changePct ?? 0,
    change24hAbs,
    logoUrl: mapped?.logoUrl ?? null,
    instrumentId,
    news: mapWidgetNewsItems(blogFeed, publicOrigin),
    research: mapWidgetResearchItems(researchFeed, publicOrigin),
    marketDataPublicBaseUrl,
    partial: !summaryRes.ok,
  }

  return NextResponse.json(payload)
}
