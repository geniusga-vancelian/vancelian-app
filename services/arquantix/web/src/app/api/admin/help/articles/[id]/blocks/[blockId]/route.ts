import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'

const updateBlockSchema = z.object({
  data: z.any().optional(),
  order: z.number().int().optional(),
})

// PUT /api/admin/help/articles/[id]/blocks/[blockId]
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

    const updateData: any = {}
    if (validated.data !== undefined) updateData.data = validated.data
    if (validated.order !== undefined) updateData.order = validated.order

    const block = await prisma.helpArticleBlock.update({
      where: { id: params.blockId },
      data: updateData,
    })

    return NextResponse.json({ block })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating block:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// DELETE /api/admin/help/articles/[id]/blocks/[blockId]
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string; blockId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    await prisma.helpArticleBlock.delete({
      where: { id: params.blockId },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting block:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









