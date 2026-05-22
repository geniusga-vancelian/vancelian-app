import { NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { ensureAppMainTabs } from '@/lib/mobile/ensureAppMainTabs'

/**
 * POST /api/admin/flutter/shell/seed
 *
 * Garantit la présence en base des entités pilotant le **shell de l'app Flutter**
 * (tab bar). **Idempotent** : ne touche pas aux libellés / cibles déjà
 * personnalisés. À appeler depuis l'admin (bouton « Initialiser ») ou en
 * post-déploiement.
 */
export async function POST() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    const result = await ensureAppMainTabs()
    return NextResponse.json({ success: true, ...result })
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/flutter/shell/seed]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 },
    )
  }
}
