import { NextRequest, NextResponse } from 'next/server'
import { loadCryptoWalletDetailNews } from '@/lib/portal/cryptoWalletDetailUpstream'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import type { PortalCryptoWalletDetailNewsPayload } from '@/lib/portal/cryptoWalletTypes'

/** Détail position crypto — section actualités liées. */
export async function GET(request: NextRequest, { params }: { params: { asset: string } }) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const asset = (params.asset ?? '').trim().toUpperCase()
  if (!asset) {
    return NextResponse.json({ error: 'invalid_asset' }, { status: 400 })
  }

  try {
    const bffOrigin = resolvePortalBffOrigin(request.nextUrl.origin)
    const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE
    return NextResponse.json(await loadCryptoWalletDetailNews(asset, bffOrigin, locale))
  } catch (error) {
    console.error('[api/portal/crypto-wallet/[asset]/news GET]', error)
    return NextResponse.json({ news: [], partial: true } satisfies PortalCryptoWalletDetailNewsPayload)
  }
}
