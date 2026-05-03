import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'

const bodySchema = z.object({
  itemId: z.string().min(1),
  direction: z.enum(['up', 'down']),
})

function isPrimaryNavRightRailRow(item: { type: string; buttonAction: string | null }) {
  const t = String(item.type)
  if (t === 'LANGUAGE_SWITCHER') return true
  return t === 'BUTTON' && !(item.buttonAction && String(item.buttonAction).trim())
}

/**
 * Réordonne uniquement les entrées BUTTON « actions droite » entre elles,
 * sans changer l’ordre relatif des liens (LINK) du menu.
 */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { itemId, direction } = bodySchema.parse(body)

    const menu = await prisma.menu.findUnique({
      where: { key: 'primary' },
      include: {
        menuItems: {
          orderBy: { order: 'asc' },
        },
      },
    })

    if (!menu) {
      return NextResponse.json({ error: 'Primary menu not found' }, { status: 404 })
    }

    const all = menu.menuItems
    const navIndices = all
      .map((item, idx) => ({ item, idx }))
      .filter(({ item }) => isPrimaryNavRightRailRow(item))
      .map(({ idx }) => idx)

    const pos = navIndices.findIndex((idx) => all[idx]!.id === itemId)
    if (pos < 0) {
      return NextResponse.json(
        { error: 'Item is not part of the reorderable right rail (lang + action buttons)' },
        { status: 400 },
      )
    }

    const swapPos = direction === 'up' ? pos - 1 : pos + 1
    if (swapPos < 0 || swapPos >= navIndices.length) {
      return NextResponse.json({ error: 'Cannot move further in this direction' }, { status: 400 })
    }

    const idxA = navIndices[pos]!
    const idxB = navIndices[swapPos]!
    const swapped = [...all]
    const tmp = swapped[idxA]!
    swapped[idxA] = swapped[idxB]!
    swapped[idxB] = tmp

    const orderedIds = swapped.map((i) => i.id)

    /**
     * `@@unique([menuId, order])` sur MenuItem : en appliquant directement 0..n-1 dans
     * l’ordre, une ligne peut recevoir `order: k` alors qu’une autre a encore ce même
     * `order` → Postgres lève une erreur d’unicité → 500.
     * Deux passes : ordres temporaires distincts, puis ordres finaux.
     */
    const TEMP_ORDER_BASE = 1_000_000
    await prisma.$transaction(async (tx) => {
      const n = orderedIds.length
      for (let i = 0; i < n; i++) {
        await tx.menuItem.update({
          where: { id: orderedIds[i]! },
          data: { order: TEMP_ORDER_BASE + i },
        })
      }
      for (let i = 0; i < n; i++) {
        await tx.menuItem.update({
          where: { id: orderedIds[i]! },
          data: { order: i },
        })
      }
    })

    return NextResponse.json({ ok: true })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 },
      )
    }
    console.error('Error reordering nav actions:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
