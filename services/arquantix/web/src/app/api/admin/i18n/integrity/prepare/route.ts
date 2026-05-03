import { NextRequest, NextResponse } from 'next/server'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import { runPrepareFixesPlan } from '@/lib/i18n/integrity/prepareFixesPlan'

/**
 * GET /api/admin/i18n/integrity/prepare?targetLocale=en|it|fr
 * Lot 2 — plan de correctifs (preview). Lecture DB uniquement. Aucune écriture.
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
    const report = await runPrepareFixesPlan(raw as Locale)
    return NextResponse.json(report, {
      headers: {
        'Cache-Control': 'no-store',
      },
    })
  } catch (e) {
    console.error('[api/admin/i18n/integrity/prepare]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
