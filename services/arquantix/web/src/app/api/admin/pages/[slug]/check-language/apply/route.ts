import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { defaultLocale, isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import {
  applyPageLanguageFixesToDraft,
  buildLanguageHintsFromScan,
  scanPageLanguage,
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
 * POST /api/admin/pages/[slug]/check-language/apply
 *
 * Corrige UNIQUEMENT les champs `WRONG_LANGUAGE` / `MIXED_LANGUAGE` détectés
 * dans le brouillon (ou publié si pas de brouillon) de chaque section, plus
 * `PageI18n.title` / `PageI18n.description` si concernés.
 *
 * - `OK` / `MISSING` / `NEEDS_REVIEW` ne sont pas modifiés.
 * - Persistance : DRAFT uniquement (PUBLISHED inchangé).
 * - Pour `targetLocale === defaultLocale`, met aussi à jour `Page.title` /
 *   `Page.description` (alignement Vault Builder).
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

    const sectionInputs: PageSectionInput[] = []
    for (const section of page.sections) {
      const draft = section.contents.find(
        (c) => c.locale === targetLocale && c.status === ContentStatus.DRAFT,
      )
      const published = section.contents.find(
        (c) => c.locale === targetLocale && c.status === ContentStatus.PUBLISHED,
      )
      const raw = draft?.data ?? published?.data
      if (raw == null || typeof raw !== 'object') continue
      sectionInputs.push({
        id: section.id,
        key: section.key,
        order: section.order,
        data: raw as Record<string, unknown>,
      })
    }

    const i18nRow = page.pageI18n.find((r) => r.locale === targetLocale)
    const pageI18nIn = {
      title: i18nRow?.title ?? page.title ?? null,
      description: i18nRow?.description ?? page.description ?? null,
    }

    // Étape 1 — scan deep préalable pour récupérer les langues détectées
    // par le LLM. Cohérence scan/apply garantie : on partage exactement
    // les mêmes décisions linguistiques que l'utilisateur a vues dans le
    // rapport « Vérifier la langue ». Tolérant à un échec OpenAI : on
    // retombe sur des hints vides → apply garde son fallback local
    // (`decideShortHeaderAction`).
    let languageHints: ReturnType<typeof buildLanguageHintsFromScan>
    let scanBefore: Awaited<ReturnType<typeof scanPageLanguageDeep>> | null = null
    try {
      scanBefore = await scanPageLanguageDeep(
        sectionInputs,
        pageI18nIn,
        targetLocale,
      )
      languageHints = buildLanguageHintsFromScan(scanBefore)
    } catch (e) {
      console.error('[pages/check-language/apply] scanBefore', e)
      languageHints = new Map()
    }

    let applied: Awaited<ReturnType<typeof applyPageLanguageFixesToDraft>>
    try {
      applied = await applyPageLanguageFixesToDraft(
        sectionInputs,
        pageI18nIn,
        targetLocale,
        { languageHints },
      )
    } catch (e) {
      console.error('[pages/check-language/apply] translate', e)
      const msg = e instanceof Error ? e.message : 'Traduction impossible'
      return NextResponse.json(
        { error: 'Correction impossible', detail: msg },
        { status: 502 },
      )
    }

    try {
      await prisma.$transaction(async (tx) => {
        // PageI18n upsert (toujours, pour tracer la locale cible).
        await tx.pageI18n.upsert({
          where: { pageId_locale: { pageId: page.id, locale: targetLocale } },
          create: {
            pageId: page.id,
            locale: targetLocale,
            title: applied.patchedPageI18n.title,
            description: applied.patchedPageI18n.description,
          },
          update: {
            title: applied.patchedPageI18n.title,
            description: applied.patchedPageI18n.description,
          },
        })

        if (targetLocale === defaultLocale) {
          const pagePatch: { title?: string | null; description?: string | null } = {}
          if (applied.patchedPageI18n.title != null)
            pagePatch.title = applied.patchedPageI18n.title
          if (applied.patchedPageI18n.description != null)
            pagePatch.description = applied.patchedPageI18n.description
          if (Object.keys(pagePatch).length > 0) {
            await tx.page.update({ where: { id: page.id }, data: pagePatch })
          }
        }

        // SectionContent upsert pour chaque section modifiée.
        for (const [sectionId, newData] of applied.patchedSections) {
          await tx.sectionContent.upsert({
            where: {
              sectionId_locale_status: {
                sectionId,
                locale: targetLocale,
                status: ContentStatus.DRAFT,
              },
            },
            create: {
              sectionId,
              locale: targetLocale,
              status: ContentStatus.DRAFT,
              data: newData as object,
              updatedByUserId: session.userId,
            },
            update: {
              data: newData as object,
              updatedByUserId: session.userId,
            },
          })
        }
      })
    } catch (e) {
      console.error('[pages/check-language/apply] persist', e)
      return NextResponse.json(
        { error: 'Échec enregistrement du brouillon.' },
        { status: 500 },
      )
    }

    // Rescan post-correction (sur la donnée corrigée en mémoire — équivalent
    // au prochain GET puisqu'on vient juste de persister).
    const sectionsAfter: PageSectionInput[] = sectionInputs.map((s) => ({
      ...s,
      data: applied.patchedSections.get(s.id) ?? s.data,
    }))
    const scanAfter = scanPageLanguage(
      sectionsAfter,
      applied.patchedPageI18n,
      targetLocale,
    )

    return NextResponse.json({
      ok: true,
      fixedFieldPaths: applied.fixedFieldPaths,
      tokensUsedApprox: applied.tokensUsedApprox,
      patchedSectionCount: applied.patchedSections.size,
      // Diagnostic des champs détectés mais non corrigés (en-têtes courts déjà
      // dans la bonne langue, ou indétectables sur la locale par défaut).
      // Permet à l'opérateur de comprendre pourquoi un champ « visible côté
      // scan » n'a pas bougé — au lieu d'un silence trompeur.
      skippedFields: applied.skippedFields,
      // Diagnostic du raffinage LLM utilisé pour piloter les hints scan→apply
      // (combien de champs reclassifiés, tokens consommés, erreurs éventuelles).
      llmRefinement: scanBefore?.llmRefinement,
      scanAfter,
    })
  } catch (e) {
    console.error('[pages/check-language/apply]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
