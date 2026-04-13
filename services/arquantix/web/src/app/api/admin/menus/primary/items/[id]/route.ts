import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { computeMenuItemUrlPath } from '@/lib/menu/computeUrlPath'

const updateMenuItemSchema = z.object({
  label: z.string().min(1).optional(),
  type: z.enum(['LINK', 'BUTTON']).optional(),
  isRoot: z.boolean().optional(),
  pageId: z.string().optional().nullable(),
  enabled: z.boolean().optional(),
  buttonStyle: z.string().optional().nullable(),
  buttonAction: z.string().optional().nullable(),
  externalUrl: z.string().optional().nullable(),
})

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
    const { label, type, isRoot, pageId, enabled, buttonStyle, buttonAction, externalUrl } = updateMenuItemSchema.parse(body)

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
      // If not root, pageId is required
      const finalPageId = pageId !== undefined ? pageId : menuItem.pageId

      if (!finalPageId) {
        return NextResponse.json(
          { error: 'pageId is required when isRoot is false' },
          { status: 400 }
        )
      }

      // Validate page exists
      const page = await prisma.page.findUnique({
        where: { id: finalPageId },
      })

      if (!page) {
        return NextResponse.json(
          { error: 'Page not found' },
          { status: 404 }
        )
      }

      updateData.isRoot = false
      updateData.pageId = finalPageId
      // Clear button fields when switching to LINK
      updateData.buttonStyle = null
      updateData.buttonAction = null
      updateData.externalUrl = null
    }

    if (label !== undefined) updateData.label = label
    if (enabled !== undefined) updateData.enabled = enabled

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
      computedUrlPath: computeMenuItemUrlPath(updated.isRoot, updated.page?.slug || null),
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

