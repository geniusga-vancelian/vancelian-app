import { NextResponse } from 'next/server'
import { z } from 'zod'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import { applyFooterLanguageFixes } from '@/lib/admin/footerCheckLanguage'
import {
  buildFooterJsonV2AfterLocaleEdit,
  getAdminFooterLoadPayload,
} from '@/lib/cms/footerStorage'
import { prisma } from '@/lib/prisma'

const bodySchema = z.object({
  targetLocale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
})

/**
 * POST /api/admin/site-footer/check-language/apply
 *
 * Applique les corrections linguistiques (OpenAI) au bloc footer de la
 * `targetLocale` et persiste le résultat dans `GlobalSettings.footerJson`.
 *
 * Pipeline cohérent avec la route page :
 *   1. scan deep → hints LLM partagés
 *   2. apply (utilise les hints, court-circuite la 2e détection)
 *   3. patch → persistance via `buildFooterJsonV2AfterLocaleEdit`
 *
 * Le footer n'a pas de notion DRAFT/PUBLISHED : l'écriture est directement
 * visible côté site public après revalidation Next (rendu serveur).
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

    const existing = await prisma.globalSettings.findFirst()
    const payload = getAdminFooterLoadPayload(existing?.footerJson ?? {})
    const block = payload.locales[targetLocale] ?? {}
    const documentDefaultLocale = payload.defaultLocale

    const { patchedBlock, apply, scan } = await applyFooterLanguageFixes(
      block,
      targetLocale,
    )

    const skippedFields = apply.skippedFields
    const llmRefinement = scan.llmRefinement

    if (apply.fixedHintKeys.length === 0) {
      return NextResponse.json({
        ok: true,
        applied: false,
        fixedFieldPaths: [],
        skippedFields,
        tokensUsedApprox: apply.tokensUsedApprox,
        llmRefinement,
      })
    }

    // Persistance : on remplace UNIQUEMENT le bloc de la `targetLocale`,
    // les autres locales restent intactes (cohérent avec le pattern PUT
    // `mode: 'locale'` du SiteFooterEditor).
    const footerToStore = buildFooterJsonV2AfterLocaleEdit({
      existingRaw: existing?.footerJson,
      locale: targetLocale,
      defaultLocale: documentDefaultLocale,
      block: patchedBlock,
    })

    if (existing) {
      await prisma.globalSettings.update({
        where: { id: existing.id },
        data: {
          footerJson: footerToStore as object,
          updatedAt: new Date(),
        },
      })
    } else {
      await prisma.globalSettings.create({
        data: {
          siteName: 'Arquantix',
          footerJson: footerToStore as object,
        },
      })
    }

    return NextResponse.json({
      ok: true,
      applied: true,
      fixedFieldPaths: apply.fixedHintKeys,
      skippedFields,
      tokensUsedApprox: apply.tokensUsedApprox,
      llmRefinement,
    })
  } catch (e) {
    console.error('[site-footer/check-language/apply]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
