import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'

const reorderSchema = z.object({
  orderedItemIds: z.array(z.string()).min(1, 'At least one item ID is required'),
})

// POST /api/admin/menus/primary/items/reorder - Reorder menu items
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { orderedItemIds } = reorderSchema.parse(body)

    // Get primary menu
    const menu = await prisma.menu.findUnique({
      where: { key: 'primary' },
      include: { menuItems: true },
    })

    if (!menu) {
      return NextResponse.json({ error: 'Primary menu not found' }, { status: 404 })
    }

    // Verify all item IDs belong to this menu
    const menuItemIds = menu.menuItems.map((item) => item.id)
    const invalidIds = orderedItemIds.filter((id) => !menuItemIds.includes(id))
    if (invalidIds.length > 0) {
      return NextResponse.json(
        { error: `Invalid item IDs: ${invalidIds.join(', ')}` },
        { status: 400 }
      )
    }

    // Verify all items are included
    if (orderedItemIds.length !== menuItemIds.length) {
      return NextResponse.json(
        { error: 'All menu items must be included in the reorder' },
        { status: 400 }
      )
    }

    // Update order in a transaction
    await prisma.$transaction(
      orderedItemIds.map((itemId, index) =>
        prisma.menuItem.update({
          where: { id: itemId },
          data: { order: index },
        })
      )
    )

    // Return updated menu with items
    const updatedMenu = await prisma.menu.findUnique({
      where: { key: 'primary' },
      include: {
        menuItems: {
          orderBy: { order: 'asc' },
        },
      },
    })

    if (!updatedMenu) {
      return NextResponse.json({ error: 'Primary menu not found' }, { status: 404 })
    }
    const { menuItems, ...menuRest } = updatedMenu
    return NextResponse.json({ menu: { ...menuRest, items: menuItems } })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error reordering menu items:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









