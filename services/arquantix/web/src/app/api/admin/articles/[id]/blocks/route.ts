import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { ArticleBlockType } from '@prisma/client'

const createBlockSchema = z.object({
  type: z.nativeEnum(ArticleBlockType),
  data: z.any(),
  order: z.number().int().optional(),
})

// GET /api/admin/articles/[id]/blocks
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const blocks = await prisma.articleBlock.findMany({
      where: { articleId: params.id },
      orderBy: { order: 'asc' },
    })

    return NextResponse.json({ blocks })
  } catch (error) {
    console.error('Error fetching blocks:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// POST /api/admin/articles/[id]/blocks
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
    const validated = createBlockSchema.parse(body)

    // Get max order
    const maxOrder = await prisma.articleBlock.findFirst({
      where: { articleId: params.id },
      orderBy: { order: 'desc' },
      select: { order: true },
    })

    const order = validated.order !== undefined ? validated.order : (maxOrder?.order ?? -1) + 1

    // Create block
    const block = await prisma.articleBlock.create({
      data: {
        articleId: params.id,
        type: validated.type,
        data: validated.data,
        order,
      },
    })

    return NextResponse.json({ block }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error creating block:', error)
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









