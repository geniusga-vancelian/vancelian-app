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

// GET /api/admin/help/categories?collectionId=...
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const collectionId = searchParams.get('collectionId')

    const where: any = {}
    if (collectionId) {
      where.collectionId = collectionId
    }

    const categories = await prisma.helpCategory.findMany({
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
            articles: {
              where: { status: 'PUBLISHED' },
            },
          },
        },
      },
    })

    return NextResponse.json({ categories })
  } catch (error) {
    console.error('Error fetching categories:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// POST /api/admin/help/categories
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = createCategorySchema.parse(body)

    const category = await prisma.helpCategory.create({
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
        { status: 400 }
      )
    }
    console.error('Error creating category:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









