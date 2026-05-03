import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { computeMenuItemUrlPath } from '@/lib/menu/computeUrlPath'
import { defaultLocale } from '@/config/locales'
import {
  primaryMenuItemContributesNavRootPageId,
  type PrimaryMenuItemForPageOrder,
} from '@/lib/cms/buildSiteTree'
import { normalizeExternalNavUrl } from '@/lib/admin/validateExternalNavUrl'

const updateMenuItemSchema = z.object({
  label: z.string().min(1).optional(),
  type: z.enum(['LINK', 'BUTTON']).optional(),
  isRoot: z.boolean().optional(),
  pageId: z.string().optional().nullable(),
  enabled: z.boolean().optional(),
  buttonStyle: z.string().optional().nullable(),
  buttonAction: z.string().optional().nullable(),
  externalUrl: z.string().optional().nullable(),
  navigationNodeKind: z.enum(['PAGE', 'GROUP', 'EXTERNAL_LINK']).optional(),
  openInNewTab: z.boolean().optional(),
})

// GET /api/admin/menus/primary/items/[id] — fiche édition (bouton zone droite ou lien barre nav niveau 1)
export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const menuItem = await prisma.menuItem.findUnique({
      where: { id: params.id },
      include: {
        menu: true,
        page: {
          select: {
            id: true,
            slug: true,
            title: true,
            urlPath: true,
            template: true,
          },
        },
        i18n: { orderBy: { locale: 'asc' } },
      },
    })

    if (!menuItem) {
      return NextResponse.json({ error: 'Menu item not found' }, { status: 404 })
    }
    if (menuItem.menu.key !== 'primary') {
      return NextResponse.json({ error: 'Not a primary menu item' }, { status: 400 })
    }

    const homePageId =
      (
        await prisma.page.findFirst({
          where: { OR: [{ pageRole: 'HOME' }, { slug: 'home' }] },
          select: { id: true },
        })
      )?.id ?? null

    const orderItem: PrimaryMenuItemForPageOrder = {
      type: String(menuItem.type),
      isRoot: menuItem.isRoot,
      pageId: menuItem.pageId,
      order: menuItem.order,
      enabled: menuItem.enabled,
      buttonStyle: menuItem.buttonStyle,
      buttonAction: menuItem.buttonAction,
      externalUrl: menuItem.externalUrl,
      navigationNodeKind: menuItem.navigationNodeKind,
      page: menuItem.page
        ? { template: menuItem.page.template, slug: menuItem.page.slug }
        : null,
    }

    const targetPageId = primaryMenuItemContributesNavRootPageId(orderItem, { homePageId })

    if (String(menuItem.type) === 'LANGUAGE_SWITCHER') {
      return NextResponse.json(
        { error: 'Cette entrée se gère depuis l’onglet Menus.' },
        { status: 400 },
      )
    }

    if (menuItem.buttonAction && String(menuItem.buttonAction).trim()) {
      return NextResponse.json(
        { error: 'This entry uses a client action; edit it from the Menus tab.' },
        { status: 400 },
      )
    }

    const isLinkStyle =
      String(menuItem.type) === 'LINK' ||
      (String(menuItem.type) === 'BUTTON' && targetPageId != null)

    if (isLinkStyle) {
      const navKind = menuItem.navigationNodeKind ?? 'PAGE'
      if (!targetPageId && navKind !== 'EXTERNAL_LINK') {
        return NextResponse.json(
          { error: 'Ce lien menu ne cible aucune page.' },
          { status: 400 },
        )
      }

      let page: {
        id: string
        slug: string
        title: string | null
        urlPath: string
      } | null =
        menuItem.page != null
          ? {
              id: menuItem.page.id,
              slug: menuItem.page.slug,
              title: menuItem.page.title,
              urlPath: menuItem.page.urlPath,
            }
          : null

      if (!page && targetPageId) {
        const p = await prisma.page.findUnique({
          where: { id: targetPageId },
          select: { id: true, slug: true, title: true, urlPath: true },
        })
        page = p
      }

      return NextResponse.json({
        item: {
          editor: 'nav_menu_link' as const,
          id: menuItem.id,
          label: menuItem.label,
          enabled: menuItem.enabled,
          isRoot: menuItem.isRoot,
          pageId: menuItem.pageId,
          navigationNodeKind: navKind,
          openInNewTab: menuItem.openInNewTab,
          externalUrl: menuItem.externalUrl,
          page,
          i18n: menuItem.i18n.map((r) => ({
            locale: r.locale,
            label: r.label,
            translationStatus: r.translationStatus,
          })),
        },
      })
    }

    if (String(menuItem.type) !== 'BUTTON') {
      return NextResponse.json({ error: 'Type d’entrée non pris en charge.' }, { status: 400 })
    }

    return NextResponse.json({
      item: {
        editor: 'nav_action' as const,
        id: menuItem.id,
        label: menuItem.label,
        externalUrl: menuItem.externalUrl,
        buttonStyle: menuItem.buttonStyle,
        enabled: menuItem.enabled,
        i18n: menuItem.i18n.map((r) => ({
          locale: r.locale,
          label: r.label,
          translationStatus: r.translationStatus,
        })),
      },
    })
  } catch (error) {
    console.error('Error fetching menu item:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

// PUT /api/admin/menus/primary/items/[id] - Update a menu item
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const {
      label,
      type,
      isRoot,
      pageId,
      enabled,
      buttonStyle,
      buttonAction,
      externalUrl,
      navigationNodeKind,
      openInNewTab,
    } = updateMenuItemSchema.parse(body)

    // Get menu item
    const menuItem = await prisma.menuItem.findUnique({
      where: { id: params.id },
      include: { menu: true, page: true },
    })

    if (!menuItem) {
      return NextResponse.json({ error: 'Menu item not found' }, { status: 404 })
    }

    if (menuItem.menu.key !== 'primary') {
      return NextResponse.json({ error: 'Menu item does not belong to primary menu' }, { status: 400 })
    }

    const updateData: any = {}
    const newType = type !== undefined ? type : menuItem.type

    // Handle type change
    if (type !== undefined) {
      updateData.type = type
      // If switching to BUTTON, clear page-related fields
      if (type === 'BUTTON') {
        updateData.isRoot = false
        updateData.pageId = null
      }
    }

    // Handle isRoot change (only for LINK type)
    const newIsRoot = isRoot !== undefined ? isRoot : menuItem.isRoot

    if (newIsRoot && navigationNodeKind === 'GROUP') {
      return NextResponse.json(
        {
          error:
            'Une entrée racine (accueil) ne peut pas être un groupe de navigation non cliquable.',
        },
        { status: 400 },
      )
    }

    if (newType === 'BUTTON') {
      // For buttons, handle button-specific fields
      if (buttonStyle !== undefined) updateData.buttonStyle = buttonStyle
      if (buttonAction !== undefined) updateData.buttonAction = buttonAction
      if (externalUrl !== undefined) updateData.externalUrl = externalUrl
      updateData.isRoot = false
      updateData.pageId = null
    } else if (newIsRoot) {
      // If switching to root, ensure no other root exists
      if (!menuItem.isRoot) {
        const existingRoot = await prisma.menuItem.findFirst({
          where: {
            menuId: menuItem.menuId,
            isRoot: true,
            id: { not: params.id },
          },
        })

        if (existingRoot) {
          return NextResponse.json(
            { error: 'A root menu item already exists. Only one root item is allowed.' },
            { status: 400 }
          )
        }
      }

      updateData.isRoot = true
      updateData.pageId = null
    } else {
      const finalPageId = pageId !== undefined ? pageId : menuItem.pageId
      const effectiveNavKind =
        navigationNodeKind ?? menuItem.navigationNodeKind ?? 'PAGE'

      if (effectiveNavKind === 'EXTERNAL_LINK') {
        const extRaw =
          externalUrl !== undefined ? externalUrl : menuItem.externalUrl
        const extParsed = normalizeExternalNavUrl(String(extRaw ?? ''))
        if (!extParsed.ok) {
          return NextResponse.json({ error: extParsed.error }, { status: 400 })
        }
        if (finalPageId) {
          const page = await prisma.page.findUnique({
            where: { id: finalPageId },
          })
          if (!page) {
            return NextResponse.json({ error: 'Page not found' }, { status: 404 })
          }
        }
        updateData.isRoot = false
        updateData.pageId = finalPageId ?? null
        updateData.buttonStyle = null
        updateData.buttonAction = null
        updateData.externalUrl = extParsed.url
      } else {
        if (!finalPageId) {
          return NextResponse.json(
            { error: 'pageId is required when isRoot is false' },
            { status: 400 },
          )
        }
        const page = await prisma.page.findUnique({
          where: { id: finalPageId },
        })
        if (!page) {
          return NextResponse.json({ error: 'Page not found' }, { status: 404 })
        }
        updateData.isRoot = false
        updateData.pageId = finalPageId
        updateData.buttonStyle = null
        updateData.buttonAction = null
        updateData.externalUrl = null
      }
    }

    if (label !== undefined) updateData.label = label
    if (enabled !== undefined) updateData.enabled = enabled
    if (navigationNodeKind !== undefined) {
      updateData.navigationNodeKind = navigationNodeKind
    }
    if (openInNewTab !== undefined) {
      updateData.openInNewTab = openInNewTab
    }

    const updated = await prisma.menuItem.update({
      where: { id: params.id },
      data: updateData,
      include: {
        page: true,
      },
    })

    // Add computedUrlPath
    const menuItemWithUrl = {
      ...updated,
      computedUrlPath: computeMenuItemUrlPath(
        updated.isRoot,
        updated.page?.slug || null,
        defaultLocale,
        updated.page?.template,
      ),
    }

    return NextResponse.json({ menuItem: menuItemWithUrl })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating menu item:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// DELETE /api/admin/menus/primary/items/[id] - Delete a menu item
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const menuItem = await prisma.menuItem.findUnique({
      where: { id: params.id },
      include: { menu: true },
    })

    if (!menuItem) {
      return NextResponse.json({ error: 'Menu item not found' }, { status: 404 })
    }

    if (menuItem.menu.key !== 'primary') {
      return NextResponse.json({ error: 'Menu item does not belong to primary menu' }, { status: 400 })
    }

    await prisma.menuItem.delete({
      where: { id: params.id },
    })

    return NextResponse.json({ message: 'Menu item deleted successfully' })
  } catch (error) {
    console.error('Error deleting menu item:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

