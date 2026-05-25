import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import {
  getLedgityMonitoringSnapshot,
  runLedgityVaultReconciliation,
} from '@/lib/portal/ledgity/ledgityVaultReconciliation'

/** Monitoring admin Ledgity vault (liquidité RWA, mismatches, pending txs). */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const pendingMinutes = Number(request.nextUrl.searchParams.get('pending_minutes') ?? '15')
    const snapshot = await getLedgityMonitoringSnapshot({
      pendingMinutes: Number.isFinite(pendingMinutes) ? pendingMinutes : 15,
    })
    return NextResponse.json(snapshot)
  } catch (error) {
    console.error('[api/admin/ledgity-vaults/monitoring GET]', error)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}

/** Déclenche réconciliation Ledgity (admin). */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const body = await request.json().catch(() => ({}))
    const action = typeof body.action === 'string' ? body.action : 'snapshot'

    if (action === 'reconcile') {
      const summary = await runLedgityVaultReconciliation()
      return NextResponse.json({ ok: true, summary })
    }

    const snapshot = await getLedgityMonitoringSnapshot()
    return NextResponse.json({ ok: true, snapshot })
  } catch (error) {
    console.error('[api/admin/ledgity-vaults/monitoring POST]', error)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}
