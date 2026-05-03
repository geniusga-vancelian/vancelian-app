import { NextRequest, NextResponse } from 'next/server'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import { runLot1LinguisticAudit } from '@/lib/i18n/integrity/runLot1Scan'

/**
 * GET /api/admin/i18n/integrity/scan?targetLocale=en|it|fr
 * Lot 1 — audit linguistique lecture seule. Aucune écriture DB.
 */
export async function GET(request: NextRequest) {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const raw = request.nextUrl.searchParams.get('targetLocale') ?? 'en'
  if (!isValidLocale(raw)) {
    return NextResponse.json(
      { error: 'Invalid targetLocale', allowed: ['fr', 'en', 'it'] },
      { status: 400 },
    )
  }

  try {
    const report = await runLot1LinguisticAudit(raw as Locale)
    return NextResponse.json(report, {
      headers: {
        'Cache-Control': 'no-store',
      },
    })
  } catch (e) {
    console.error('[api/admin/i18n/integrity/scan]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
