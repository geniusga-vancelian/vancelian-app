import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { awaitRouteParams } from '@/lib/api/routeParams'
import { adminRouteErrorBody } from '@/lib/api/adminRouteErrorBody'

const reorderSchema = z.object({
  orderedBlockIds: z.array(z.string()).min(1),
})

// POST /api/admin/articles/[id]/blocks/reorder
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } | Promise<{ id: string }> }
) {
  try {
    const { id: articleId } = await awaitRouteParams(params)
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    let body: unknown
    try {
      body = await request.json()
    } catch {
      return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
    }
    const { orderedBlockIds } = reorderSchema.parse(body)

    // Verify all blocks belong to this article and the list is complete (évite ordres dupliqués).
    const [blocks, articleBlockCount] = await Promise.all([
      prisma.articleBlock.findMany({
        where: {
          id: { in: orderedBlockIds },
          articleId,
        },
      }),
      prisma.articleBlock.count({ where: { articleId } }),
    ])

    if (blocks.length !== orderedBlockIds.length) {
      return NextResponse.json(
        { error: 'Some blocks not found or do not belong to this article' },
        { status: 400 }
      )
    }

    if (articleBlockCount !== orderedBlockIds.length) {
      return NextResponse.json(
        { error: 'orderedBlockIds must include every block of this article' },
        { status: 400 }
      )
    }

    // `@@unique([articleId, order])` : des updates en parallèle vers les mêmes `order`
    // provoquent P2002 (contrainte unique). Deux phases dans une transaction.
    await prisma.$transaction(async (tx) => {
      for (let i = 0; i < orderedBlockIds.length; i++) {
        await tx.articleBlock.update({
          where: { id: orderedBlockIds[i] },
          data: { order: -(i + 1) },
        })
      }
      for (let i = 0; i < orderedBlockIds.length; i++) {
        await tx.articleBlock.update({
          where: { id: orderedBlockIds[i] },
          data: { order: i },
        })
      }
    })

    return NextResponse.json({ message: 'Blocks reordered' })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error reordering blocks:', error)
    return NextResponse.json(adminRouteErrorBody(error), { status: 500 })
  }
}









