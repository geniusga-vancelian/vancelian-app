import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { defaultLocale, isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

function emptyToNull(s: string | null | undefined): string | null {
  if (s == null) return null
  const t = s.trim()
  return t.length > 0 ? t : null
}

const bodySchema = z.object({
  locale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
  title: z.string().max(500).nullable(),
  description: z.string().max(2000).nullable(),
  navMegaCategory: z.string().max(120).nullable(),
  navMegaDescription: z.string().max(500).nullable(),
  navMegaIconMediaId: z.union([z.string().cuid(), z.null()]).optional(),
})

/**
 * PATCH /api/admin/pages/[slug]/locale-metadata
 *
 * Met à jour les métadonnées éditoriales par locale (PageI18n) + optionnellement l’icône méga-menu (Page, globale).
 * Préférer `PATCH …/nav-mega-icon` pour ne modifier que le média (UI admin).
 * Pour la locale par défaut, synchronise aussi `Page.title` / `Page.description`.
 */
export async function PATCH(
  request: NextRequest,
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

    const json = await request.json().catch(() => ({}))
    const parsed = bodySchema.safeParse(json)
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Invalid body', details: parsed.error.flatten() },
        { status: 400 },
      )
    }

    const {
      locale,
      title,
      description,
      navMegaCategory,
      navMegaDescription,
      navMegaIconMediaId,
    } = parsed.data
    const loc = locale as Locale

    const page = await prisma.page.findUnique({
      where: { slug },
      select: { id: true, title: true, description: true },
    })
    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    const t = emptyToNull(title)
    const d = emptyToNull(description)
    const megaCat = emptyToNull(navMegaCategory)
    const megaDesc = emptyToNull(navMegaDescription)

    if (navMegaIconMediaId != null) {
      const media = await prisma.media.findUnique({
        where: { id: navMegaIconMediaId },
        select: { id: true },
      })
      if (!media) {
        return NextResponse.json({ error: 'Media not found' }, { status: 400 })
      }
    }

    await prisma.$transaction(async (tx) => {
      await tx.pageI18n.upsert({
        where: { pageId_locale: { pageId: page.id, locale: loc } },
        create: {
          pageId: page.id,
          locale: loc,
          title: t,
          description: d,
          navMegaCategory: megaCat,
          navMegaDescription: megaDesc,
          ogTitle: null,
          ogDescription: null,
        },
        update: {
          title: t,
          description: d,
          navMegaCategory: megaCat,
          navMegaDescription: megaDesc,
        },
      })

      const pageData: {
        title?: string | null
        description?: string | null
        navMegaIconMediaId?: string | null
      } = {}

      if (loc === defaultLocale) {
        pageData.title = t
        pageData.description = d
      }

      if (navMegaIconMediaId !== undefined) {
        pageData.navMegaIconMediaId = navMegaIconMediaId
      }

      if (Object.keys(pageData).length > 0) {
        await tx.page.update({
          where: { id: page.id },
          data: pageData,
        })
      }
    })

    const updated = await prisma.page.findUnique({
      where: { id: page.id },
      include: {
        navMegaIconMedia: {
          select: {
            id: true,
            url: true,
            filename: true,
            alt: true,
            mimeType: true,
          },
        },
        pageI18n: {
          select: {
            locale: true,
            title: true,
            description: true,
            navMegaCategory: true,
            navMegaDescription: true,
          },
        },
      },
    })

    return NextResponse.json({ ok: true, page: updated })
  } catch (e) {
    console.error('[pages/locale-metadata PATCH]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
