import { NextRequest, NextResponse } from 'next/server'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { buildPortalInvestPayload } from '@/lib/portal/investFormat'
import type { PortalInvestPayload } from '@/lib/portal/investTypes'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'

export async function GET(request: NextRequest) {
  try {
    const token = await readPortalAccessToken()
    if (!token) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const origin = resolvePortalBffOrigin(request.nextUrl.origin)
    const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE
    const catalogBase = `${origin}/api/mobile/flutter/catalog/products`
    const catalogQs = `locale=${encodeURIComponent(locale)}&include_engine_data=true&limit=50`
    const [eoRes, vaultRes] = await Promise.all([
      fetch(`${catalogBase}?type=exclusive_offer&${catalogQs}`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(20000),
      }),
      fetch(`${catalogBase}?type=vault_simple&${catalogQs}`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(20000),
      }),
    ])

    const eoJson = await eoRes.json().catch(() => null)
    const vaultJson = await vaultRes.json().catch(() => null)
    if (!eoRes.ok) {
      return NextResponse.json(eoJson ?? { error: 'upstream_error' }, { status: eoRes.status })
    }
    if (!vaultRes.ok) {
      return NextResponse.json(vaultJson ?? { error: 'upstream_error' }, { status: vaultRes.status })
    }

    const exclusiveOffers = (eoJson as { products?: unknown[] })?.products ?? []
    const vaultProducts = (vaultJson as { products?: unknown[] })?.products ?? []
    const payload: PortalInvestPayload = buildPortalInvestPayload(
      exclusiveOffers as never[],
      vaultProducts as never[],
    )

    return NextResponse.json(payload)
  } catch (error) {
    console.error('[api/portal/invest GET]', error)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}
