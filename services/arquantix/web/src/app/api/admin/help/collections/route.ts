import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { defaultLocale } from '@/config/locales'
import { TranslationStatus, ContentStatus } from '@prisma/client'

const colorHexSchema = z.string().regex(/^#(?:[0-9a-fA-F]{6})$/, 'Invalid hex color')

const createCollectionSchema = z.object({
  slug: z.string().min(1),
  title: z.string().min(1),
  subtitle: z.string().nullable().optional(),
  iconKey: z.string().min(1).default('article'),
  colorHex: colorHexSchema.default('#0F172A'),
  order: z.number().int().default(0),
  isPublished: z.boolean().default(true),
  coverMediaId: z.string().min(1).nullable().optional(),
})

// GET /api/admin/help/collections
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const collections = await prisma.helpCollection.findMany({
      orderBy: { order: 'asc' },
      include: {
        i18n: true,
        categories: {
          where: { isPublished: true },
          include: {
            articles: {
              where: { status: ContentStatus.PUBLISHED },
              select: { id: true },
            },
          },
        },
      },
    })

    // Calculate counts per collection
    const collectionsWithCounts = collections.map((col) => {
      const categoryCount = col.categories.length
      const articleCount = col.categories.reduce(
        (sum, cat) => sum + (cat.articles?.length || 0),
        0
      )
      return {
        id: col.id,
        slug: col.slug,
        iconKey: col.iconKey,
        colorHex: col.colorHex,
        coverMediaId: col.coverMediaId,
        order: col.order,
        isPublished: col.isPublished,
        i18n: col.i18n,
        _count: {
          categories: categoryCount,
          articles: articleCount,
        },
      }
    })

    return NextResponse.json({ collections: collectionsWithCounts })
  } catch (error: any) {
    console.error('Error fetching collections:', error)
    console.error('Error details:', error.message, error.stack)
    return NextResponse.json(
      { error: 'Internal server error', details: error.message },
      { status: 500 }
    )
  }
}

// POST /api/admin/help/collections
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = createCollectionSchema.parse(body)

    // Check if slug already exists
    const existing = await prisma.helpCollection.findUnique({
      where: { slug: validated.slug },
    })

    if (existing) {
      return NextResponse.json(
        { error: 'Collection with this slug already exists' },
        { status: 409 }
      )
    }

    const collection = await prisma.helpCollection.create({
      data: {
        slug: validated.slug,
        iconKey: validated.iconKey,
        colorHex: validated.colorHex,
        order: validated.order,
        isPublished: validated.isPublished,
        ...(validated.coverMediaId !== undefined
          ? { coverMediaId: validated.coverMediaId }
          : {}),
        i18n: {
          create: {
            locale: defaultLocale,
            title: validated.title,
            subtitle: validated.subtitle || null,
            translationStatus: TranslationStatus.ORIGINAL,
          },
        },
      },
      include: {
        i18n: true,
      },
    })

    return NextResponse.json({ collection })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Error creating collection:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

