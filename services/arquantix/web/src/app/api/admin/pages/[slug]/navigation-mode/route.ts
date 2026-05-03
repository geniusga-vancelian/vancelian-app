import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { MenuItemType, MenuNavigationNodeKind } from '@prisma/client'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

const bodySchema = z.object({
  mode: z.enum(['content_page', 'navigation_hub']),
})

/**
 * PATCH /api/admin/pages/[slug]/navigation-mode
 *
 * Bascule les `MenuItem` du menu **primaire** liés à cette page entre
 * `PAGE` (page avec contenu, cliquable) et `GROUP` (hub, non cliquable).
 * Ne modifie pas les sections, le slug, `showInMegaMenu`, ni les traductions.
 */
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> | { slug: string } },
) {
  try {
    const resolved = await Promise.resolve(params)
    const slug = normalizeSlug(resolved?.slug)
    if (!slug) {
      return NextResponse.json({ error: 'Slug invalide' }, { status: 400 })
    }

    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const json = await request.json().catch(() => ({}))
    const parsed = bodySchema.safeParse(json)
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Corps de requête invalide', details: parsed.error.flatten() },
        { status: 400 },
      )
    }

    const page = await prisma.page.findUnique({
      where: { slug },
      select: { id: true },
    })
    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    const items = await prisma.menuItem.findMany({
      where: {
        pageId: page.id,
        menu: { key: 'primary' },
      },
      select: {
        id: true,
        type: true,
        isRoot: true,
        navigationNodeKind: true,
      },
    })

    const navigable = items.filter((i) => i.type !== MenuItemType.LANGUAGE_SWITCHER)

    if (navigable.length === 0) {
      return NextResponse.json(
        {
          error:
            'Aucun item du menu primaire ne pointe vers cette page. Liez d’abord la page dans la structure du site.',
          code: 'UNLINKED',
        },
        { status: 409 },
      )
    }

    if (
      navigable.some((i) => i.navigationNodeKind === MenuNavigationNodeKind.EXTERNAL_LINK)
    ) {
      return NextResponse.json(
        {
          error:
            'Cette page est liée à un lien externe dans le menu. Modifiez le type depuis l’éditeur de lien du menu (barre de navigation).',
          code: 'EXTERNAL_LINK',
        },
        { status: 409 },
      )
    }

    if (parsed.data.mode === 'navigation_hub') {
      if (navigable.some((i) => i.isRoot)) {
        return NextResponse.json(
          {
            error:
              'L’entrée d’accueil (racine) ne peut pas être un hub de navigation non cliquable.',
            code: 'ROOT_CONFLICT',
          },
          { status: 400 },
        )
      }
    }

    const targetKind =
      parsed.data.mode === 'navigation_hub'
        ? MenuNavigationNodeKind.GROUP
        : MenuNavigationNodeKind.PAGE

    await prisma.menuItem.updateMany({
      where: { id: { in: navigable.map((n) => n.id) } },
      data: { navigationNodeKind: targetKind },
    })

    const warnings: string[] = []
    if (navigable.length > 1) {
      warnings.push(
        `${navigable.length} entrées du menu primaire pointent vers cette page : elles ont toutes été synchronisées sur le même mode.`,
      )
    }

    return NextResponse.json({
      ok: true,
      mode: parsed.data.mode,
      navigationNodeKind: targetKind,
      updatedMenuItemIds: navigable.map((n) => n.id),
      warnings,
    })
  } catch (e) {
    console.error('[pages/navigation-mode PATCH]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
