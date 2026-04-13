import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'

export const dynamic = 'force-dynamic'

/**
 * Resolve a product code or UUID to the FastAPI product UUID.
 * If the identifier is already a UUID (contains '-'), returns it directly.
 * Otherwise, looks up by product_code in the full products list (includes brouillons / non publiés).
 *
 * Important: `product-catalog` only returns is_public=true — bundles en brouillon n’y figurent pas
 * et le graphique restait vide (404 côté proxy) alors que l’allocation s’affichait.
 */
async function resolveProductId(identifier: string): Promise<string | null> {
  if (identifier.includes('-')) return identifier
  try {
    const listUrl = new URL(buildBackendUrl('/api/portfolio-engine/products'))
    listUrl.searchParams.set('limit', '200')
    const res = await fetch(listUrl.toString(), {
      signal: AbortSignal.timeout(8000),
      cache: 'no-store',
    })
    if (!res.ok) return null
    const data = (await res.json()) as { items?: Array<{ id: string; product_code: string }> }
    const match = data.items?.find(
      (p) => p.product_code.toUpperCase() === identifier.toUpperCase(),
    )
    return match?.id ?? null
  } catch {
    return null
  }
}

/**
 * GET /api/mobile/flutter/portfolio-products/[productCode]/chart-history?period=1a
 *
 * Proxies to FastAPI: /api/portfolio-engine/products/{uuid}/chart-history?period=...
 * Returns the weighted composite performance chart for a bundle product.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ productCode: string }> | { productCode: string } },
) {
  try {
    const resolved = await Promise.resolve(params)
    const rawCode = (resolved?.productCode ?? '').trim()
    if (!rawCode) {
      return NextResponse.json({ error: 'Missing productCode' }, { status: 400 })
    }

    const period = request.nextUrl.searchParams.get('period') || '1a'

    const productId = await resolveProductId(rawCode)
    if (!productId) {
      return NextResponse.json({ error: 'Product not found' }, { status: 404 })
    }

    const chartUrl = new URL(
      buildBackendUrl(`/api/portfolio-engine/products/${productId}/chart-history`),
    )
    chartUrl.searchParams.set('period', period)
    const backendRes = await fetch(chartUrl.toString(), {
      signal: AbortSignal.timeout(15000),
      cache: 'no-store',
    })

    if (!backendRes.ok) {
      const text = await backendRes.text().catch(() => '')
      console.error(
        `[chart-history proxy] Backend ${backendRes.status}: ${text.substring(0, 500)}`,
      )
      return NextResponse.json(
        { error: 'Chart data unavailable' },
        { status: backendRes.status },
      )
    }

    const payload = await backendRes.json()
    return NextResponse.json(payload)
  } catch (error) {
    console.error('[chart-history proxy]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
