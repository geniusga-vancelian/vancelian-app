import { NextResponse } from 'next/server'
import { ContentStatus, TranslationStatus } from '@prisma/client'
import { z } from 'zod'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

/**
 * POST /api/admin/pages/[slug]/publish
 *
 * Publie toutes les sections d'une page **pour une seule locale** :
 * pour chaque section possédant un DRAFT (`SectionContent` `status=DRAFT`)
 * pour la `targetLocale`, on copie son `data` + `translationStatus` vers
 * la ligne PUBLISHED (upsert).
 *
 * - **Pas de modification de `Page.*` ni `PageI18n.*`** (déjà sans notion
 *   DRAFT/PUBLISHED — visible immédiatement à la sauvegarde).
 * - **Aucune section sans DRAFT n'est touchée** : `PUBLISHED` reste
 *   intact (raison `no-draft`).
 * - Transaction Prisma : tout ou rien.
 *
 * Réponse :
 * ```ts
 * {
 *   ok: true,
 *   targetLocale: 'fr',
 *   totalSections: 8,
 *   publishedSectionsCount: 3,
 *   skippedSectionsCount: 5,
 *   sectionsPublished: [{ id, key, hadPublishedBefore }],
 *   sectionsSkipped:   [{ id, key, reason: 'no-draft' }],
 *   warnings: string[],
 * }
 * ```
 */

const bodySchema = z.object({
  targetLocale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
})

function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

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
        sections: {
          orderBy: { order: 'asc' },
          include: {
            contents: {
              where: { locale: targetLocale },
            },
          },
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    type PublishPlanItem = {
      sectionId: string
      sectionKey: string
      data: unknown
      translationStatus: TranslationStatus
      hadPublishedBefore: boolean
    }

    const plan: PublishPlanItem[] = []
    const skipped: Array<{ id: string; key: string; reason: 'no-draft' }> = []
    const warnings: string[] = []

    for (const section of page.sections) {
      const draft = section.contents.find((c) => c.status === ContentStatus.DRAFT)
      const published = section.contents.find((c) => c.status === ContentStatus.PUBLISHED)
      if (!draft) {
        skipped.push({ id: section.id, key: section.key, reason: 'no-draft' })
        continue
      }
      if (draft.translationStatus === TranslationStatus.MACHINE) {
        warnings.push(
          `Section « ${section.key} » : brouillon en traduction machine non approuvée — sera publié tel quel.`,
        )
      }
      plan.push({
        sectionId: section.id,
        sectionKey: section.key,
        data: draft.data,
        translationStatus: draft.translationStatus,
        hadPublishedBefore: !!published,
      })
    }

    if (plan.length === 0) {
      return NextResponse.json({
        ok: true,
        targetLocale,
        totalSections: page.sections.length,
        publishedSectionsCount: 0,
        skippedSectionsCount: skipped.length,
        sectionsPublished: [],
        sectionsSkipped: skipped,
        warnings,
      })
    }

    try {
      await prisma.$transaction(async (tx) => {
        for (const item of plan) {
          await tx.sectionContent.upsert({
            where: {
              sectionId_locale_status: {
                sectionId: item.sectionId,
                locale: targetLocale,
                status: ContentStatus.PUBLISHED,
              },
            },
            create: {
              sectionId: item.sectionId,
              locale: targetLocale,
              status: ContentStatus.PUBLISHED,
              data: item.data as object,
              translationStatus: item.translationStatus,
              updatedByUserId: session.userId,
            },
            update: {
              data: item.data as object,
              translationStatus: item.translationStatus,
              updatedByUserId: session.userId,
            },
          })
        }
      })
    } catch (e) {
      console.error('[pages/publish] persist', e)
      return NextResponse.json(
        { error: 'Échec de la publication.' },
        { status: 500 },
      )
    }

    return NextResponse.json({
      ok: true,
      targetLocale,
      totalSections: page.sections.length,
      publishedSectionsCount: plan.length,
      skippedSectionsCount: skipped.length,
      sectionsPublished: plan.map((p) => ({
        id: p.sectionId,
        key: p.sectionKey,
        hadPublishedBefore: p.hadPublishedBefore,
      })),
      sectionsSkipped: skipped,
      warnings,
    })
  } catch (e) {
    console.error('[pages/publish]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
