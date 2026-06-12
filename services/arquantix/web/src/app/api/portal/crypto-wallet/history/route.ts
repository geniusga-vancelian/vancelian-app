import { NextResponse } from 'next/server'
import {
  parseWalletHistoryPerformance,
  parseWalletHistoryPoints,
} from '@/lib/portal/cryptoWalletFormat'
import { fetchPortalUpstreamJsonSafe } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import type { PortalCryptoWalletHistoryPayload } from '@/lib/portal/cryptoWalletTypes'

/** Hub wallet crypto — section historique de performance (courbe). */
export async function GET() {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const history = await fetchPortalUpstreamJsonSafe(
      '/api/app/wallet/history?period=ALL&mode=performance_value&scope=crypto',
    )

    return NextResponse.json({
      historyPoints: history.ok ? parseWalletHistoryPoints(history.data) : [],
      performance: history.ok ? parseWalletHistoryPerformance(history.data) : null,
      partial: !history.ok,
    } satisfies PortalCryptoWalletHistoryPayload)
  } catch (error) {
    console.error('[api/portal/crypto-wallet/history GET]', error)
    return NextResponse.json({
      historyPoints: [],
      performance: null,
      partial: true,
    } satisfies PortalCryptoWalletHistoryPayload)
  }
}
