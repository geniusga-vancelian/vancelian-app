import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import {
  mergeTranslateStats,
  translatePageI18nFromFr,
  translateVaultDraftJsonFromFr,
  verifyTranslatedVaultDraft,
} from '@/lib/admin/vaultAutoTranslateEngine'
import { prisma } from '@/lib/prisma'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'

const bodySchema = z.object({
  targetLocale: z.enum(['en', 'it']),
})

function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

/**
 * POST /api/admin/vaults/[slug]/auto-translate-locale
 * Pipeline : clone FR → traduction OpenAI (allowlist) → vérif linguistique → écriture DRAFT cible + PageI18n uniquement.
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
      return NextResponse.json({ error: 'Invalid body', details: parsed.error.flatten() }, { status: 400 })
    }

    const { targetLocale } = parsed.data

    const page = await prisma.page.findFirst({
      where: { slug, template: VAULT_TEMPLATE_DB },
      include: {
        pageI18n: true,
        sections: {
          where: { key: VAULT_SECTION_KEY },
          take: 1,
          include: { contents: true },
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Vault not found' }, { status: 404 })
    }

    const section = page.sections[0]
    if (!section) {
      return NextResponse.json({ error: 'Vault section not found' }, { status: 400 })
    }

    const contents = section.contents
    const frDraft = contents.find((c) => c.locale === 'fr' && c.status === ContentStatus.DRAFT)
    const frPublished = contents.find((c) => c.locale === 'fr' && c.status === ContentStatus.PUBLISHED)
    const frSource = frDraft?.data ?? frPublished?.data

    if (frSource == null || typeof frSource !== 'object') {
      return NextResponse.json(
        { error: 'Aucun contenu français (brouillon ou publié) à utiliser comme source.' },
        { status: 400 },
      )
    }

    const frSourceKind: 'draft' | 'published' = frDraft?.data != null ? 'draft' : 'published'

    const frI18n = page.pageI18n.find((r) => r.locale === 'fr')
    const titleFr = (frI18n?.title ?? page.title ?? '').trim() || null
    const descFr = (frI18n?.description ?? page.description ?? '').trim() || null

    let translatedVault: Record<string, unknown>
    let i18nOut: { title: string | null; description: string | null }
    let mergedStats: { fieldsTranslated: number; tokensUsedApprox: number }

    const existingTargetI18n = page.pageI18n.find((r) => r.locale === targetLocale)

    try {
      const i18nTr = await translatePageI18nFromFr(titleFr, descFr, targetLocale)
      const vaultTr = await translateVaultDraftJsonFromFr(frSource as Record<string, unknown>, targetLocale)
      mergedStats = mergeTranslateStats(i18nTr.stats, vaultTr.stats)
      translatedVault = vaultTr.data
      let titleOut = i18nTr.title
      let descOut = i18nTr.description
      if (titleFr == null) {
        titleOut = existingTargetI18n?.title ?? null
      }
      if (descFr == null) {
        descOut = existingTargetI18n?.description ?? null
      }
      i18nOut = { title: titleOut, description: descOut }
    } catch (e) {
      console.error('[auto-translate-locale] translate', e)
      const msg = e instanceof Error ? e.message : 'Traduction impossible'
      return NextResponse.json(
        { error: 'Traduction échouée — aucune écriture en base.', detail: msg },
        { status: 502 },
      )
    }

    const verify = verifyTranslatedVaultDraft(
      translatedVault,
      targetLocale,
      page.slug,
      page.id,
    )

    try {
      await prisma.$transaction(async (tx) => {
        await tx.pageI18n.upsert({
          where: { pageId_locale: { pageId: page.id, locale: targetLocale } },
          create: {
            pageId: page.id,
            locale: targetLocale,
            title: i18nOut.title,
            description: i18nOut.description,
          },
          update: {
            title: i18nOut.title,
            description: i18nOut.description,
          },
        })

        await tx.sectionContent.upsert({
          where: {
            sectionId_locale_status: {
              sectionId: section.id,
              locale: targetLocale,
              status: ContentStatus.DRAFT,
            },
          },
          create: {
            sectionId: section.id,
            locale: targetLocale,
            status: ContentStatus.DRAFT,
            data: translatedVault as object,
            updatedByUserId: session.userId,
          },
          update: {
            data: translatedVault as object,
            updatedByUserId: session.userId,
          },
        })
      })
    } catch (e) {
      console.error('[auto-translate-locale] persist', e)
      return NextResponse.json(
        { error: 'Échec enregistrement du brouillon — réessayez.' },
        { status: 500 },
      )
    }

    return NextResponse.json({
      ok: true,
      phases: {
        copy: { ok: true, frSource: frSourceKind },
        translate: {
          ok: true,
          fieldsTranslated: mergedStats.fieldsTranslated,
          tokensUsedApprox: mergedStats.tokensUsedApprox,
        },
        verify: {
          ok: true,
          totalFindings: verify.findings.length,
          suspiciousCount: verify.suspiciousCount,
          byStatus: verify.byStatus,
          sampleFindings: verify.findings.slice(0, 24).map((f) => ({
            fieldPath: f.fieldPath,
            status: f.status,
            excerpt: f.excerpt,
          })),
        },
      },
    })
  } catch (e) {
    console.error('[api/admin/vaults/auto-translate-locale]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
