import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'

const createCategorySchema = z.object({
  collectionId: z.string().min(1),
  slug: z.string().min(1),
  order: z.number().int().default(0),
  isPublished: z.boolean().default(true),
})

// GET /api/admin/academy/categories?collectionId=...
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const collectionId = searchParams.get('collectionId')

    const where: Record<string, unknown> = {}
    if (collectionId) {
      where.collectionId = collectionId
    }

    const categories = await prisma.academyCategory.findMany({
      where,
      orderBy: { order: 'asc' },
      include: {
        i18n: true,
        collection: {
          include: {
            i18n: {
              where: { locale: 'fr' },
              take: 1,
            },
          },
        },
        _count: {
          select: {
            unifiedArticles: {
              where: { status: 'PUBLISHED', articleType: 'ACADEMY' },
            },
          },
        },
      },
    })

    return NextResponse.json({ categories })
  } catch (error) {
    console.error('Error fetching academy categories:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

// POST /api/admin/academy/categories
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = createCategorySchema.parse(body)

    const category = await prisma.academyCategory.create({
      data: {
        collectionId: validated.collectionId,
        slug: validated.slug,
        order: validated.order,
        isPublished: validated.isPublished,
      },
    })

    return NextResponse.json({ category })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 },
      )
    }
    console.error('Error creating academy category:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
