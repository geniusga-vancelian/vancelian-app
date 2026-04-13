import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { Prisma } from '@prisma/client'

const reorderSchema = z.object({
  orderedBlockIds: z.array(z.string()).min(1),
})

// POST /api/admin/articles/[id]/blocks/reorder
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { orderedBlockIds } = reorderSchema.parse(body)

    // Verify all blocks belong to this article and the list is complete (évite ordres dupliqués).
    const [blocks, articleBlockCount] = await Promise.all([
      prisma.articleBlock.findMany({
        where: {
          id: { in: orderedBlockIds },
          articleId: params.id,
        },
      }),
      prisma.articleBlock.count({ where: { articleId: params.id } }),
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
    const message = error instanceof Error ? error.message : 'Unknown error'
    const code =
      error instanceof Prisma.PrismaClientKnownRequestError ? error.code : undefined
    return NextResponse.json(
      {
        error: 'Internal server error',
        ...(process.env.NODE_ENV === 'development' && { message, code }),
      },
      { status: 500 }
    )
  }
}









