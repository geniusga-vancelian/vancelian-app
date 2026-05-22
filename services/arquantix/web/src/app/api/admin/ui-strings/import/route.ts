import path from 'node:path'

import { NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { readArbDirectory } from '@/lib/i18n/uiStrings/arbReader'
import { extractArbToDb } from '@/lib/i18n/uiStrings/extractor'
import { getSiteI18nSettingsUncached } from '@/lib/i18n/siteI18nSettings'

/**
 * POST /api/admin/ui-strings/import
 *
 * Relance l'extraction ARB → DB (idempotente) **sans toucher aux overrides**.
 *
 * Cas d'usage : on vient d'ajouter une key dans `app_en.arb` côté Flutter,
 * on clique « Re-importer ARB » dans l'admin pour la voir apparaître sans
 * relancer le serveur ni passer par la CLI.
 */
export async function POST() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    /// Le BFF Next tourne dans `services/arquantix/web`. On résout l'ARB
    /// relativement, comme le script CLI.
    const arbDir = path.resolve(process.cwd(), '..', 'mobile', 'lib', 'l10n')
    const arbs = await readArbDirectory(arbDir)
    if (arbs.length === 0) {
      return NextResponse.json(
        { error: `No ARB files found in ${arbDir}` },
        { status: 404 },
      )
    }

    const i18n = await getSiteI18nSettingsUncached()
    const stats = await extractArbToDb(prisma, arbs, {
      defaultLocale: i18n.defaultLocale,
      strictKeys: false,
    })

    return NextResponse.json({
      success: true,
      arbDir,
      locales: arbs.map((a) => a.locale),
      stats,
    })
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/ui-strings/import POST]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 },
    )
  }
}
