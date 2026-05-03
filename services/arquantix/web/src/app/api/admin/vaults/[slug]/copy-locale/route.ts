import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { defaultLocale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'

const bodySchema = z.object({
  fromLocale: z.enum(['fr', 'en', 'it']),
  toLocale: z.enum(['fr', 'en', 'it']),
})

function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

export async function POST(
  _req: Request,
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

    const body = await _req.json().catch(() => ({}))
    const parsed = bodySchema.safeParse(body)
    if (!parsed.success) {
      return NextResponse.json({ error: 'Invalid body', details: parsed.error.flatten() }, { status: 400 })
    }

    const { fromLocale, toLocale } = parsed.data
    if (fromLocale === toLocale) {
      return NextResponse.json({ error: 'fromLocale and toLocale must differ' }, { status: 400 })
    }

    const page = await prisma.page.findFirst({
      where: {
        slug,
        template: VAULT_TEMPLATE_DB,
      },
      include: {
        pageI18n: true,
        sections: {
          where: { key: VAULT_SECTION_KEY },
          take: 1,
          include: {
            contents: true,
          },
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

    const fromI18n = page.pageI18n.find((r) => r.locale === fromLocale)
    const fromTitle = fromI18n?.title ?? null
    const fromDesc = fromI18n?.description ?? null

    await prisma.pageI18n.upsert({
      where: { pageId_locale: { pageId: page.id, locale: toLocale } },
      create: {
        pageId: page.id,
        locale: toLocale,
        title: fromTitle,
        description: fromDesc,
      },
      update: {
        title: fromTitle,
        description: fromDesc,
      },
    })

    if (toLocale === defaultLocale && (fromTitle !== null || fromDesc !== null)) {
      await prisma.page.update({
        where: { id: page.id },
        data: {
          ...(fromTitle !== null ? { title: fromTitle } : {}),
          ...(fromDesc !== null ? { description: fromDesc } : {}),
        },
      })
    }

    const contents = section.contents
    const fromDraft = contents.find((c) => c.locale === fromLocale && c.status === ContentStatus.DRAFT)
    const fromPublished = contents.find((c) => c.locale === fromLocale && c.status === ContentStatus.PUBLISHED)
    const sourceData = fromDraft?.data ?? fromPublished?.data

    if (sourceData != null) {
      const dataClone = JSON.parse(JSON.stringify(sourceData)) as object
      await prisma.sectionContent.upsert({
        where: {
          sectionId_locale_status: {
            sectionId: section.id,
            locale: toLocale,
            status: ContentStatus.DRAFT,
          },
        },
        create: {
          sectionId: section.id,
          locale: toLocale,
          status: ContentStatus.DRAFT,
          data: dataClone,
          updatedByUserId: session.userId,
        },
        update: {
          data: dataClone,
          updatedByUserId: session.userId,
        },
      })
    }

    return NextResponse.json({ success: true })
  } catch (e) {
    console.error('[api/admin/vaults/copy-locale]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
