import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'

const bodySchema = z.object({
  locale: z.enum(['fr', 'en', 'it']),
})

function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

/**
 * POST — copie le SectionContent DRAFT vers PUBLISHED pour une locale (vault_builder_v1).
 * N’altère pas les autres langues ni PageI18n.
 */
export async function POST(
  req: Request,
  { params }: { params: Promise<{ slug: string }> | { slug: string } }
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

    const json = await req.json().catch(() => ({}))
    const parsed = bodySchema.safeParse(json)
    if (!parsed.success) {
      return NextResponse.json({ error: 'Invalid body', details: parsed.error.flatten() }, { status: 400 })
    }

    const loc = parsed.data.locale as Locale
    if (!isValidLocale(loc)) {
      return NextResponse.json({ error: 'Invalid locale' }, { status: 400 })
    }

    const page = await prisma.page.findFirst({
      where: {
        slug,
        template: VAULT_TEMPLATE_DB,
      },
      include: {
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

    const draftRow = section.contents.find((c) => c.locale === loc && c.status === ContentStatus.DRAFT)
    if (!draftRow) {
      return NextResponse.json(
        { error: 'Aucun brouillon à publier pour cette langue.' },
        { status: 400 },
      )
    }

    const data = draftRow.data
    if (data == null) {
      return NextResponse.json(
        { error: 'Brouillon sans données — enregistrez le vault avant de publier.' },
        { status: 400 },
      )
    }

    await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: section.id,
          locale: loc,
          status: ContentStatus.PUBLISHED,
        },
      },
      create: {
        sectionId: section.id,
        locale: loc,
        status: ContentStatus.PUBLISHED,
        data: data as object,
        updatedByUserId: session.userId,
      },
      update: {
        data: data as object,
        updatedByUserId: session.userId,
      },
    })

    return NextResponse.json({ success: true, locale: loc })
  } catch (e) {
    console.error('[api/admin/vaults/publish-locale]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
