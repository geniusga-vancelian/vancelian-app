import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { getLombardMonitoringSnapshot } from '@/lib/portal/lombard/lombardMonitoring'

/** Monitoring admin Lombard V1 (positions, LTV bands, ledger tx stats). */
export async function GET(_request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const snapshot = await getLombardMonitoringSnapshot()
    return NextResponse.json(snapshot)
  } catch (error) {
    console.error('[api/admin/lombard/monitoring GET]', error)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}
