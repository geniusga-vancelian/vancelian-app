import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

const bodySchema = z
  .object({
    navMegaIconMediaId: z.union([z.string().cuid(), z.null()]).optional(),
    showInMegaMenu: z.boolean().optional(),
  })
  .refine((d) => d.navMegaIconMediaId !== undefined || d.showInMegaMenu !== undefined, {
    message: 'Au moins un champ requis (icône ou visibilité méga-menu).',
  })

/**
 * PATCH /api/admin/pages/[slug]/nav-mega-icon
 *
 * Met à jour l’icône méga-menu et/ou la visibilité en tant qu’enfant dans le méga-menu (`Page`, hors traduction).
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

    const { navMegaIconMediaId, showInMegaMenu } = parsed.data

    const page = await prisma.page.findUnique({
      where: { slug },
      select: { id: true },
    })
    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    if (navMegaIconMediaId != null) {
      const media = await prisma.media.findUnique({
        where: { id: navMegaIconMediaId },
        select: { id: true },
      })
      if (!media) {
        return NextResponse.json({ error: 'Media not found' }, { status: 400 })
      }
    }

    const data: { navMegaIconMediaId?: string | null; showInMegaMenu?: boolean } = {}
    if (navMegaIconMediaId !== undefined) {
      data.navMegaIconMediaId = navMegaIconMediaId
    }
    if (showInMegaMenu !== undefined) {
      data.showInMegaMenu = showInMegaMenu
    }

    await prisma.page.update({
      where: { id: page.id },
      data,
    })

    return NextResponse.json({ ok: true })
  } catch (e) {
    console.error('[pages/nav-mega-icon PATCH]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
