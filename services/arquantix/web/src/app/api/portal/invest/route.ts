import { NextRequest, NextResponse } from 'next/server'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { buildPortalInvestPayload } from '@/lib/portal/investFormat'
import type { PortalInvestPayload } from '@/lib/portal/investTypes'

export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const origin = request.nextUrl.origin
  const locale = request.nextUrl.searchParams.get('locale')?.trim() || 'fr'
  const url = `${origin}/api/mobile/flutter/catalog/products?type=exclusive_offer&locale=${encodeURIComponent(locale)}&include_engine_data=true&limit=50`

  const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(20000) })
  const json = await res.json().catch(() => null)
  if (!res.ok) {
    return NextResponse.json(json ?? { error: 'upstream_error' }, { status: res.status })
  }

  const products = (json as { products?: unknown[] })?.products ?? []
  const payload: PortalInvestPayload = buildPortalInvestPayload(products as never[])

  return NextResponse.json(payload)
}
