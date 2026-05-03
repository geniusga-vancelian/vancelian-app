import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { defaultLocale } from '@/config/locales'
import { isValidLocale, type Locale } from '@/config/locales'
import {
  applyVaultLanguageFixesToDraft,
  scanVaultModuleLanguage,
} from '@/lib/admin/vaultCheckModuleLanguage'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'

const bodySchema = z.object({
  targetLocale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
})

function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

/**
 * POST /api/admin/vaults/[slug]/check-module-language/apply
 * Corrige en DRAFT uniquement les champs WRONG_LANGUAGE / MIXED_LANGUAGE (allowlist).
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

    const targetLocale = parsed.data.targetLocale as Locale

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
    const draft = contents.find((c) => c.locale === targetLocale && c.status === ContentStatus.DRAFT)
    const published = contents.find((c) => c.locale === targetLocale && c.status === ContentStatus.PUBLISHED)
    const sourceData = draft?.data ?? published?.data

    if (sourceData == null || typeof sourceData !== 'object') {
      return NextResponse.json(
        { error: `Aucun contenu source pour ${targetLocale} (créez un brouillon ou publiez d’abord).` },
        { status: 400 },
      )
    }

    const i18nRow = page.pageI18n.find((r) => r.locale === targetLocale)
    const pageI18nIn = {
      title: i18nRow?.title ?? page.title ?? null,
      description: i18nRow?.description ?? page.description ?? null,
    }

    let applied: Awaited<ReturnType<typeof applyVaultLanguageFixesToDraft>>
    try {
      applied = await applyVaultLanguageFixesToDraft(
        sourceData as Record<string, unknown>,
        pageI18nIn,
        targetLocale,
        page.slug,
        page.id,
      )
    } catch (e) {
      console.error('[check-module-language/apply] translate', e)
      const msg = e instanceof Error ? e.message : 'Traduction impossible'
      return NextResponse.json({ error: 'Correction impossible', detail: msg }, { status: 502 })
    }

    try {
      await prisma.$transaction(async (tx) => {
        await tx.pageI18n.upsert({
          where: { pageId_locale: { pageId: page.id, locale: targetLocale } },
          create: {
            pageId: page.id,
            locale: targetLocale,
            title: applied.pageI18n.title,
            description: applied.pageI18n.description,
          },
          update: {
            title: applied.pageI18n.title,
            description: applied.pageI18n.description,
          },
        })

        if (targetLocale === defaultLocale) {
          const pagePatch: { title?: string | null; description?: string | null } = {}
          if (applied.pageI18n.title != null) pagePatch.title = applied.pageI18n.title
          if (applied.pageI18n.description != null) pagePatch.description = applied.pageI18n.description
          if (Object.keys(pagePatch).length > 0) {
            await tx.page.update({
              where: { id: page.id },
              data: pagePatch,
            })
          }
        }

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
            data: applied.vaultData as object,
            updatedByUserId: session.userId,
          },
          update: {
            data: applied.vaultData as object,
            updatedByUserId: session.userId,
          },
        })
      })
    } catch (e) {
      console.error('[check-module-language/apply] persist', e)
      return NextResponse.json({ error: 'Échec enregistrement du brouillon.' }, { status: 500 })
    }

    const scanAfter = scanVaultModuleLanguage(
      applied.vaultData,
      applied.pageI18n,
      targetLocale,
      page.slug,
      page.id,
    )

    return NextResponse.json({
      ok: true,
      fixedFieldPaths: applied.fixedFieldPaths,
      tokensUsedApprox: applied.tokensUsedApprox,
      verifyAfter: applied.verifyAfter,
      scanAfter,
    })
  } catch (e) {
    console.error('[check-module-language/apply]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
