import { NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import { getMarketDataPublicBaseUrl } from '@/lib/portal/marketDataPublic'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { mapAllCryptoList } from '@/lib/portal/marketsFormat'

/** Liste complète crypto — chargée à la demande (onglet All crypto). */
export async function GET() {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const res = await fetch(buildBackendUrl('/api/market-data/all-crypto'), {
      signal: AbortSignal.timeout(20000),
      next: { revalidate: 30 },
    })
    const data = await res.json().catch(() => null)
    if (!res.ok) {
      return NextResponse.json({ error: 'upstream_error', items: [] }, { status: 502 })
    }

    const rows =
      (data as { summaries?: unknown })?.summaries ?? (Array.isArray(data) ? data : null)
    const marketDataPublicBaseUrl = getMarketDataPublicBaseUrl()
    const items = mapAllCryptoList(rows, {
      currency: 'USD',
      logoBaseUrl: marketDataPublicBaseUrl,
    })

    return NextResponse.json({ items, marketDataPublicBaseUrl })
  } catch {
    return NextResponse.json({ error: 'timeout', items: [] }, { status: 504 })
  }
}
