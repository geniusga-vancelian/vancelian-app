import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import { scanVaultModuleLanguage } from '@/lib/admin/vaultCheckModuleLanguage'
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
 * POST /api/admin/vaults/[slug]/check-module-language/scan
 * Analyse tous les champs allowlistés pour la locale cible — aucune écriture.
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
    const rawData = draft?.data ?? published?.data

    if (rawData == null || typeof rawData !== 'object') {
      return NextResponse.json(
        { error: `Aucun contenu pour la locale ${targetLocale} (brouillon ou publié).` },
        { status: 400 },
      )
    }

    const data = rawData as Record<string, unknown>
    const layer: 'draft' | 'published' = draft?.data != null ? 'draft' : 'published'

    const i18nRow = page.pageI18n.find((r) => r.locale === targetLocale)
    const pageI18n = {
      title: i18nRow?.title ?? page.title ?? null,
      description: i18nRow?.description ?? page.description ?? null,
    }

    const result = scanVaultModuleLanguage(data, pageI18n, targetLocale, page.slug, page.id)

    return NextResponse.json({
      ok: true,
      contentLayerRead: layer,
      result,
    })
  } catch (e) {
    console.error('[check-module-language/scan]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
