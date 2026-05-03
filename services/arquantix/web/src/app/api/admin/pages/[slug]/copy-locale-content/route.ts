import { NextRequest, NextResponse } from 'next/server'
import type { Prisma } from '@prisma/client'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { defaultLocale, isValidLocale } from '@/config/locales'

const bodySchema = z.object({
  sourceLocale: z.string().refine(isValidLocale),
  targetLocale: z.string().refine(isValidLocale),
  /** Toujours écrire en DRAFT côté cible (recommandé — pas de magie sur le publié). */
  writeAsDraft: z.boolean().optional().default(true),
})

/**
 * POST /api/admin/pages/[slug]/copy-locale-content
 * Copie prudente : contenu source (PUBLISHED prioritaire, sinon DRAFT) → DRAFT sur la locale cible.
 * Duplique aussi les entrées PageI18n quand présentes ; sinon titre/description Page pour la locale source par défaut uniquement.
 * Pas de traduction automatique : copie brute pour relecture éditoriale.
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { slug: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const json = await request.json().catch(() => ({}))
    const parsed = bodySchema.safeParse(json)
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Invalid body', details: parsed.error.flatten() },
        { status: 400 },
      )
    }

    const { sourceLocale, targetLocale, writeAsDraft } = parsed.data
    if (sourceLocale === targetLocale) {
      return NextResponse.json(
        { error: 'sourceLocale et targetLocale doivent différer' },
        { status: 400 },
      )
    }

    if (!writeAsDraft) {
      return NextResponse.json(
        { error: 'Seule la cible DRAFT est supportée pour ce lot (writeAsDraft doit être true)' },
        { status: 400 },
      )
    }

    const page = await prisma.page.findUnique({
      where: { slug: params.slug },
      include: {
        pageI18n: true,
        sections: {
          include: {
            contents: true,
          },
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    let sectionsCopied = 0
    let pageI18nUpdated = false

    await prisma.$transaction(async (tx) => {
      for (const section of page.sections) {
        const contents = section.contents
        const sourcePublished = contents.find(
          (c) => c.locale === sourceLocale && c.status === 'PUBLISHED',
        )
        const sourceDraft = contents.find(
          (c) => c.locale === sourceLocale && c.status === 'DRAFT',
        )
        const source = sourcePublished ?? sourceDraft
        if (!source) continue

        const data = source.data as Prisma.InputJsonValue

        await tx.sectionContent.upsert({
          where: {
            sectionId_locale_status: {
              sectionId: section.id,
              locale: targetLocale,
              status: 'DRAFT',
            },
          },
          create: {
            sectionId: section.id,
            locale: targetLocale,
            status: 'DRAFT',
            data,
            translationStatus: 'ORIGINAL',
          },
          update: {
            data,
            translationStatus: 'ORIGINAL',
          },
        })
        sectionsCopied++
      }

      const sourcePi = page.pageI18n.find((r) => r.locale === sourceLocale)
      if (sourcePi) {
        await tx.pageI18n.upsert({
          where: {
            pageId_locale: { pageId: page.id, locale: targetLocale },
          },
          create: {
            pageId: page.id,
            locale: targetLocale,
            title: sourcePi.title,
            description: sourcePi.description,
            ogTitle: sourcePi.ogTitle,
            ogDescription: sourcePi.ogDescription,
            navMegaCategory: sourcePi.navMegaCategory,
            navMegaDescription: sourcePi.navMegaDescription,
          },
          update: {
            title: sourcePi.title,
            description: sourcePi.description,
            ogTitle: sourcePi.ogTitle,
            ogDescription: sourcePi.ogDescription,
            navMegaCategory: sourcePi.navMegaCategory,
            navMegaDescription: sourcePi.navMegaDescription,
          },
        })
        pageI18nUpdated = true
      } else if (sourceLocale === defaultLocale) {
        await tx.pageI18n.upsert({
          where: {
            pageId_locale: { pageId: page.id, locale: targetLocale },
          },
          create: {
            pageId: page.id,
            locale: targetLocale,
            title: page.title,
            description: page.description,
            ogTitle: null,
            ogDescription: null,
          },
          update: {
            title: page.title,
            description: page.description,
          },
        })
        pageI18nUpdated = true
      }
    })

    return NextResponse.json({
      ok: true,
      slug: page.slug,
      sourceLocale,
      targetLocale,
      sectionsCopied,
      pageI18nUpdated,
      note:
        'Contenu copié en brouillon sur la locale cible. Publiez section par section depuis l’éditeur si besoin.',
    })
  } catch (error) {
    console.error('copy-locale-content:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 },
    )
  }
}
