import { NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import { getMarketDataPublicBaseUrl } from '@/lib/portal/marketDataPublic'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import {
  mapAllCryptoList,
  mergeAllCryptoSparklines,
  PORTAL_DEFAULT_CRYPTO_SYMBOLS,
} from '@/lib/portal/marketsFormat'

/** Liste complète crypto — chargée à la demande (onglet All crypto). */
export async function GET() {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const symbols = PORTAL_DEFAULT_CRYPTO_SYMBOLS.join(',')
    const [allCryptoRes, summaryRes] = await Promise.all([
      fetch(buildBackendUrl('/api/market-data/all-crypto'), {
        signal: AbortSignal.timeout(20000),
        next: { revalidate: 30 },
      }),
      fetch(
        buildBackendUrl(
          `/api/market-data/market-summary?symbols=${encodeURIComponent(symbols)}`,
        ),
        {
          signal: AbortSignal.timeout(20000),
          next: { revalidate: 30 },
        },
      ),
    ])

    const data = await allCryptoRes.json().catch(() => null)
    if (!allCryptoRes.ok) {
      return NextResponse.json({ error: 'upstream_error', items: [] }, { status: 502 })
    }

    const summaryJson = summaryRes.ok ? await summaryRes.json().catch(() => null) : null
    const summaryRows =
      (summaryJson as { summaries?: unknown })?.summaries ??
      (Array.isArray(summaryJson) ? summaryJson : [])

    const rows = mergeAllCryptoSparklines(
      (data as { summaries?: unknown })?.summaries ?? (Array.isArray(data) ? data : null),
      summaryRows,
    )

    const marketDataPublicBaseUrl = getMarketDataPublicBaseUrl()
    const items = mapAllCryptoList(rows, {
      currency: 'USD',
      logoBaseUrl: marketDataPublicBaseUrl,
    })

    return NextResponse.json({ items, marketDataPublicBaseUrl })
  } catch {
    return NextResponse.json(
      { error: 'timeout', items: [], marketDataPublicBaseUrl: getMarketDataPublicBaseUrl(), partial: true },
      { status: 200 },
    )
  }
}
