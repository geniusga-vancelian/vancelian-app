import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import {
  scanPageLanguageDeep,
  type PageSectionInput,
} from '@/lib/admin/pageCheckLanguage'
import { prisma } from '@/lib/prisma'

const bodySchema = z.object({
  targetLocale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
})

function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

/**
 * POST /api/admin/pages/[slug]/check-language/scan
 *
 * Analyse linguistique de TOUTES les sections traduisibles de la page (selon
 * `SECTION_I18N_POLICIES`) + `PageI18n` pour `targetLocale`. Lecture seule.
 *
 * Pour chaque section, priorité au DRAFT de la locale cible, fallback PUBLISHED.
 *
 * Pendant le Vault Builder `check-module-language/scan` mais ouvert au modèle
 * page CMS générique (template != `vault_builder`).
 */
export async function POST(
  req: Request,
  { params }: { params: Promise<{ slug: string }> | { slug: string } },
) {
  try {
    const resolved = await Promise.resolve(params)
    const slug = normalizeSlug(resolved?.slug)
    if (!slug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }

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

    const page = await prisma.page.findUnique({
      where: { slug },
      include: {
        pageI18n: true,
        sections: {
          orderBy: { order: 'asc' },
          include: { contents: true },
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    // Compose la liste des sections avec leur `data` pour la locale cible
    // (priorité brouillon, fallback publié, sinon section écartée).
    const sectionInputs: PageSectionInput[] = []
    let layerDraftCount = 0
    let layerPublishedCount = 0
    let layerMissingCount = 0

    for (const section of page.sections) {
      const draft = section.contents.find(
        (c) => c.locale === targetLocale && c.status === ContentStatus.DRAFT,
      )
      const published = section.contents.find(
        (c) => c.locale === targetLocale && c.status === ContentStatus.PUBLISHED,
      )
      const raw = draft?.data ?? published?.data
      if (raw == null || typeof raw !== 'object') {
        layerMissingCount += 1
        continue
      }
      if (draft?.data != null) layerDraftCount += 1
      else layerPublishedCount += 1
      sectionInputs.push({
        id: section.id,
        key: section.key,
        order: section.order,
        data: raw as Record<string, unknown>,
      })
    }

    const i18nRow = page.pageI18n.find((r) => r.locale === targetLocale)
    const pageI18n = {
      title: i18nRow?.title ?? page.title ?? null,
      description: i18nRow?.description ?? page.description ?? null,
    }

    // Scan deep : passage local synchrone (franc + heuristique) + 1 appel
    // OpenAI batché pour reclassifier les champs ambigus (NEEDS_REVIEW +
    // faibles confiances). Tolérant aux pannes : si OpenAI échoue, on
    // retombe sur le scan local (`llmRefinement.hadError = true`).
    const result = await scanPageLanguageDeep(
      sectionInputs,
      pageI18n,
      targetLocale,
    )

    return NextResponse.json({
      ok: true,
      contentLayerSummary: {
        draftSections: layerDraftCount,
        publishedSections: layerPublishedCount,
        missingSections: layerMissingCount,
      },
      result,
    })
  } catch (e) {
    console.error('[pages/check-language/scan]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
