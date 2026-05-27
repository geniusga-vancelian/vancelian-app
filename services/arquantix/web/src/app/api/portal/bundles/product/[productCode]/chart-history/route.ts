import { NextRequest, NextResponse } from 'next/server'

import { parseBundleChartPoints } from '@/lib/portal/bundleProductFormat'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

export async function GET(
  request: NextRequest,
  { params }: { params: { productCode: string } },
) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const productCode = (params.productCode ?? '').trim()
  if (!productCode) {
    return NextResponse.json({ error: 'invalid_product_code' }, { status: 400 })
  }

  const period = request.nextUrl.searchParams.get('period')?.trim() || '1a'
  const bffOrigin = resolvePortalBffOrigin(request.nextUrl.origin)
  const url = `${bffOrigin}/api/mobile/flutter/portfolio-products/${encodeURIComponent(productCode)}/chart-history?period=${encodeURIComponent(period)}`

  const res = await fetch(url, {
    cache: 'no-store',
    signal: AbortSignal.timeout(15000),
  })

  if (!res.ok) {
    return NextResponse.json({ error: 'chart_unavailable' }, { status: res.status })
  }

  const data = await res.json().catch(() => null)
  const { performancePct, historyPoints } = parseBundleChartPoints(data)

  return NextResponse.json({
    period,
    performancePct,
    historyPoints,
  })
}
