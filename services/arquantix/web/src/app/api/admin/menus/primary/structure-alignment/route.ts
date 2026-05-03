import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import {
  buildAdminSiteDisplayTreeFromPages,
  extractPrimaryMenuPageIdOrder,
} from '@/lib/cms/buildSiteTree'
import {
  buildPostSyncItemOrder,
  computeMenuStructureReport,
  flattenNavTreePreorder,
} from '@/lib/admin/menuStructureAlignment'

async function loadPrimaryMenuWithPages() {
  let menu = await prisma.menu.findUnique({
    where: { key: 'primary' },
    include: {
      menuItems: {
        orderBy: { order: 'asc' },
        include: { page: true },
      },
    },
  })
  if (!menu) {
    menu = await prisma.menu.create({
      data: {
        key: 'primary',
        name: 'Primary Menu',
        menuItems: {
          create: {
            label: 'Home',
            isRoot: true,
            pageId: null,
            order: 0,
            enabled: true,
          },
        },
      },
      include: {
        menuItems: {
          orderBy: { order: 'asc' },
          include: { page: true },
        },
      },
    })
  }
  return menu
}

async function loadTree() {
  const [pages, primaryMenu] = await Promise.all([
    prisma.page.findMany({
      orderBy: [{ parentId: 'asc' }, { sortOrder: 'asc' }, { createdAt: 'asc' }],
      include: {
        packagedProduct: {
          select: { id: true, slug: true, productType: true },
        },
      },
    }),
    prisma.menu.findUnique({
      where: { key: 'primary' },
      select: {
        menuItems: {
          where: { enabled: true },
          orderBy: { order: 'asc' },
          select: {
            type: true,
            isRoot: true,
            pageId: true,
            order: true,
            buttonStyle: true,
            buttonAction: true,
            externalUrl: true,
            page: { select: { template: true, slug: true } },
          },
        },
      },
    }),
  ])
  const homePageId =
    pages.find((p) => p.slug === 'home' || p.pageRole === 'HOME')?.id ?? null
  const blogPageId = pages.find((p) => p.slug === 'blog')?.id ?? null
  const menuOrder = extractPrimaryMenuPageIdOrder(primaryMenu?.menuItems ?? [], {
    homePageId,
    blogPageId,
  })
  return buildAdminSiteDisplayTreeFromPages(pages, menuOrder)
}

/**
 * GET — écarts menu ↔ arborescence (pages showInNav, ordre, chemins vault, etc.)
 */
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const menu = await loadPrimaryMenuWithPages()
    const tree = await loadTree()
    const report = computeMenuStructureReport(tree, menu.menuItems)
    const roots = menu.menuItems.filter((i) => i.isRoot)

    return NextResponse.json({
      ...report,
      applyHints: {
        missingCount: report.missingMenuPageIds.length,
        canAddMissing: report.missingMenuPageIds.length > 0,
        canReorder: roots.length === 1,
      },
    })
  } catch (e) {
    console.error('structure-alignment GET:', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

const applySchema = z
  .object({
    addMissing: z.boolean().default(false),
    reorderNavLinks: z.boolean().default(false),
  })
  .refine((d) => d.addMissing || d.reorderNavLinks, {
    message: 'Choisissez au moins une action',
  })

/**
 * POST — synchronisation contrôlée : ajout des liens manquants et/ou réordonnancement des entrées.
 * Les boutons (CTA) et liens externes ne sont pas supprimés ; les libellés existants sont conservés.
 */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = applySchema.parse(await request.json())
    const menu = await loadPrimaryMenuWithPages()
    const tree = await loadTree()
    let items = menu.menuItems

    if (body.reorderNavLinks) {
      const roots = items.filter((i) => i.isRoot)
      if (roots.length !== 1) {
        return NextResponse.json(
          {
            error:
              'Réordonnancement impossible : le menu doit avoir exactement un élément racine (accueil).',
            code: 'ROOT_COUNT',
          },
          { status: 400 },
        )
      }
    }

    await prisma.$transaction(async (tx) => {
      let current = await tx.menuItem.findMany({
        where: { menuId: menu.id },
        include: { page: true },
        orderBy: { order: 'asc' },
      })

      if (body.addMissing) {
        const navPages = flattenNavTreePreorder(tree)
        const have = new Set(current.filter((i) => i.pageId).map((i) => i.pageId!))
        let nextOrder = current.reduce((m, i) => Math.max(m, i.order), -1) + 1
        for (const p of navPages) {
          if (have.has(p.id)) continue
          await tx.menuItem.create({
            data: {
              menuId: menu.id,
              label: p.title?.trim() || p.slug,
              type: 'LINK',
              isRoot: false,
              pageId: p.id,
              order: nextOrder,
              enabled: true,
            },
          })
          nextOrder += 1
        }
        current = await tx.menuItem.findMany({
          where: { menuId: menu.id },
          include: { page: true },
          orderBy: { order: 'asc' },
        })
      }

      if (body.reorderNavLinks) {
        const n = current.length
        for (let i = 0; i < n; i++) {
          await tx.menuItem.update({
            where: { id: current[i].id },
            data: { order: 1_000_000 + i },
          })
        }
        current = await tx.menuItem.findMany({
          where: { menuId: menu.id },
          include: { page: true },
          orderBy: { order: 'asc' },
        })
        const orderedIds = buildPostSyncItemOrder(current, tree)
        for (let o = 0; o < orderedIds.length; o++) {
          await tx.menuItem.update({
            where: { id: orderedIds[o] },
            data: { order: o },
          })
        }
      }
    })

    const updated = await prisma.menu.findUnique({
      where: { key: 'primary' },
      include: { menuItems: { orderBy: { order: 'asc' } } },
    })

    return NextResponse.json({
      ok: true,
      menuItemCount: updated?.menuItems.length ?? 0,
      applied: { addMissing: body.addMissing, reorderNavLinks: body.reorderNavLinks },
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Données invalides', issues: error.issues },
        { status: 400 },
      )
    }
    console.error('structure-alignment POST:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
