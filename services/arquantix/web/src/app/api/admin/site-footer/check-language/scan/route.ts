import { NextResponse } from 'next/server'
import { z } from 'zod'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import { scanFooterLanguageDeep } from '@/lib/admin/footerCheckLanguage'
import { getAdminFooterLoadPayload } from '@/lib/cms/footerStorage'
import { prisma } from '@/lib/prisma'

const bodySchema = z.object({
  targetLocale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
})

/**
 * POST /api/admin/site-footer/check-language/scan
 *
 * Scan linguistique deep (local + affinage IA OpenAI batché) du bloc footer
 * pour la `targetLocale`. Lecture seule : ne modifie pas la base.
 *
 * Réponse : `result` (entries + summary + llmRefinement) — même shape que la
 * route page pour permettre la réutilisation des helpers UI de la modale.
 */
export async function POST(req: Request) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await req.json().catch(() => ({}))
    const parsed = bodySchema.safeParse(body)
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Invalid body', details: parsed.error.flatten() },
        { status: 400 },
      )
    }

    const targetLocale = parsed.data.targetLocale as Locale

    const row = await prisma.globalSettings.findFirst()
    const payload = getAdminFooterLoadPayload(row?.footerJson ?? {})
    const block = payload.locales[targetLocale] ?? {}

    const result = await scanFooterLanguageDeep(block, targetLocale)

    return NextResponse.json({
      ok: true,
      footerStorage: {
        formatVersion: payload.formatVersion,
        isLegacyStorage: payload.isLegacyStorage,
        defaultLocale: payload.defaultLocale,
      },
      result,
    })
  } catch (e) {
    console.error('[site-footer/check-language/scan]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
