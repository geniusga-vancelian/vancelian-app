import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { computeMenuItemUrlPath } from '@/lib/menu/computeUrlPath'

const createMenuItemSchema = z.object({
  label: z.string().min(1, 'Label is required'),
  type: z.enum(['LINK', 'BUTTON']).default('LINK'),
  isRoot: z.boolean().default(false),
  pageId: z.string().optional().nullable(),
  enabled: z.boolean().default(true),
  buttonStyle: z.string().optional().nullable(),
  buttonAction: z.string().optional().nullable(),
  externalUrl: z.string().optional().nullable(),
})

// POST /api/admin/menus/primary/items - Create a new menu item
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { label, type, isRoot, pageId, enabled, buttonStyle, buttonAction, externalUrl } = createMenuItemSchema.parse(body)

    // Get primary menu
    const menu = await prisma.menu.findUnique({
      where: { key: 'primary' },
      include: { menuItems: true },
    })

    if (!menu) {
      return NextResponse.json({ error: 'Primary menu not found' }, { status: 404 })
    }

    // Validation: if isRoot=true, pageId must be null
    if (isRoot && pageId) {
      return NextResponse.json(
        { error: 'pageId must be null when isRoot is true' },
        { status: 400 }
      )
    }

    // Validation: for LINK type, if isRoot=false, pageId is required
    if (type === 'LINK' && !isRoot && !pageId) {
      return NextResponse.json(
        { error: 'pageId is required when isRoot is false for LINK type' },
        { status: 400 }
      )
    }

    // Validation: for BUTTON type, pageId should be null (buttons don't link to pages)
    if (type === 'BUTTON' && pageId) {
      return NextResponse.json(
        { error: 'pageId must be null for BUTTON type' },
        { status: 400 }
      )
    }

    // Validation: ensure page exists if pageId provided
    if (pageId) {
      const page = await prisma.page.findUnique({
        where: { id: pageId },
      })

      if (!page) {
        return NextResponse.json(
          { error: 'Page not found' },
          { status: 404 }
        )
      }
    }

    // Validation: ensure only one root item exists
    if (isRoot) {
      const existingRoot = await prisma.menuItem.findFirst({
        where: {
          menuId: menu.id,
          isRoot: true,
        },
      })

      if (existingRoot) {
        return NextResponse.json(
          { error: 'A root menu item already exists. Only one root item is allowed.' },
          { status: 400 }
        )
      }
    }

    // Get last order
    const lastItem = await prisma.menuItem.findFirst({
      where: { menuId: menu.id },
      orderBy: { order: 'desc' },
    })

    const order = lastItem ? lastItem.order + 1 : 0

    // Create menu item
    const menuItem = await prisma.menuItem.create({
      data: {
        menuId: menu.id,
        label,
        type,
        isRoot: type === 'BUTTON' ? false : isRoot, // Buttons are never root
        pageId: type === 'BUTTON' ? null : (isRoot ? null : pageId),
        order,
        enabled,
        buttonStyle: type === 'BUTTON' ? buttonStyle : null,
        buttonAction: type === 'BUTTON' ? buttonAction : null,
        externalUrl: type === 'BUTTON' ? externalUrl : null,
      },
      include: {
        page: true,
      },
    })

    // Add computedUrlPath
    const menuItemWithUrl = {
      ...menuItem,
      computedUrlPath: computeMenuItemUrlPath(menuItem.isRoot, menuItem.page?.slug || null),
    }

    return NextResponse.json({ menuItem: menuItemWithUrl }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error creating menu item:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

