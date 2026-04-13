import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { ArticleBlockType } from '@prisma/client'
import { isValidLocale } from '@/config/locales'

const createBlockSchema = z.object({
  type: z.nativeEnum(ArticleBlockType),
  data: z.any(),
  locale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
  order: z.number().int().optional(),
})

// GET /api/admin/help/articles/[id]/blocks?locale=...
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const locale = searchParams.get('locale') || 'fr'

    const blocks = await prisma.helpArticleBlock.findMany({
      where: {
        articleId: params.id,
        locale,
      },
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

// POST /api/admin/help/articles/[id]/blocks
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

    // Get max order for this locale
    const maxOrder = await prisma.helpArticleBlock.findFirst({
      where: {
        articleId: params.id,
        locale: validated.locale,
      },
      orderBy: { order: 'desc' },
      select: { order: true },
    })

    const order = validated.order !== undefined ? validated.order : (maxOrder?.order ?? -1) + 1

    // Create block
    const block = await prisma.helpArticleBlock.create({
      data: {
        articleId: params.id,
        locale: validated.locale,
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
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









