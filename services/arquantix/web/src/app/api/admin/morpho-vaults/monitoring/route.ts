import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import {
  getMorphoMonitoringSnapshot,
  runMorphoVaultReconciliation,
} from '@/lib/portal/morphoVaultReconciliation'
import { syncMorphoVaultRegistryFromConfigs } from '@/lib/portal/morphoVaultRegistrySync'

/** Monitoring admin Morpho vault (assets, mismatches, pending txs). */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const pendingMinutes = Number(request.nextUrl.searchParams.get('pending_minutes') ?? '15')
    const snapshot = await getMorphoMonitoringSnapshot({
      pendingMinutes: Number.isFinite(pendingMinutes) ? pendingMinutes : 15,
    })
    return NextResponse.json(snapshot)
  } catch (error) {
    console.error('[api/admin/morpho-vaults/monitoring GET]', error)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}

/** Déclenche sync registry et/ou réconciliation (admin). */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const body = await request.json().catch(() => ({}))
    const action = typeof body.action === 'string' ? body.action : 'snapshot'

    if (action === 'sync_registry') {
      const result = await syncMorphoVaultRegistryFromConfigs()
      return NextResponse.json({ ok: true, result })
    }

    if (action === 'reconcile') {
      const summary = await runMorphoVaultReconciliation()
      return NextResponse.json({ ok: true, summary })
    }

    const snapshot = await getMorphoMonitoringSnapshot()
    return NextResponse.json({ ok: true, snapshot })
  } catch (error) {
    console.error('[api/admin/morpho-vaults/monitoring POST]', error)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}
