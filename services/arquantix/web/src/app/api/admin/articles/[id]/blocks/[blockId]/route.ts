import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { ArticleBlockType, Prisma } from '@prisma/client'

const updateBlockSchema = z.object({
  type: z.nativeEnum(ArticleBlockType).optional(),
  data: z.any().optional(),
  order: z.number().int().optional(),
})

// PUT /api/admin/articles/[id]/blocks/[blockId]
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string; blockId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = updateBlockSchema.parse(body)

    const block = await prisma.articleBlock.findUnique({
      where: { id: params.blockId },
    })

    if (!block || block.articleId !== params.id) {
      return NextResponse.json({ error: 'Block not found' }, { status: 404 })
    }

    let dataPayload: Prisma.InputJsonValue | undefined
    if (validated.data !== undefined) {
      try {
        // Prisma Json n’accepte que des valeurs JSON ; repasser par stringify évite
        // fonctions, symboles, références circulaires ou types non sérialisables.
        dataPayload = JSON.parse(JSON.stringify(validated.data)) as Prisma.InputJsonValue
      } catch {
        return NextResponse.json(
          { error: 'Block data must be JSON-serializable' },
          { status: 400 }
        )
      }
    }

    // Update block
    const updated = await prisma.articleBlock.update({
      where: { id: params.blockId },
      data: {
        ...(validated.type && { type: validated.type }),
        ...(validated.data !== undefined && { data: dataPayload }),
        ...(validated.order !== undefined && { order: validated.order }),
      },
    })

    return NextResponse.json({ block: updated })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating block:', error)
    const message = error instanceof Error ? error.message : 'Unknown error'
    return NextResponse.json(
      {
        error: 'Internal server error',
        ...(process.env.NODE_ENV === 'development' && { message }),
      },
      { status: 500 }
    )
  }
}

// DELETE /api/admin/articles/[id]/blocks/[blockId]
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string; blockId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const block = await prisma.articleBlock.findUnique({
      where: { id: params.blockId },
    })

    if (!block || block.articleId !== params.id) {
      return NextResponse.json({ error: 'Block not found' }, { status: 404 })
    }

    await prisma.articleBlock.delete({
      where: { id: params.blockId },
    })

    return NextResponse.json({ message: 'Block deleted' })
  } catch (error) {
    console.error('Error deleting block:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









