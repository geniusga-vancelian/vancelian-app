import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { defaultLocale } from '@/config/locales'
import { TranslationStatus } from '@prisma/client'

const createArticleSchema = z.object({
  categoryId: z.string().min(1),
  slug: z.string().min(1),
  title: z.string().min(1),
})

// GET /api/admin/help/articles?categoryId=...&status=...&locale=...
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const categoryId = searchParams.get('categoryId')
    const status = searchParams.get('status')
    const locale = searchParams.get('locale') || 'fr'

    const where: any = {}
    if (categoryId) {
      where.categoryId = categoryId
    }
    if (status && status !== 'ALL') {
      where.status = status
    }

    const articles = await prisma.helpArticle.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      include: {
        i18n: {
          where: { locale },
          take: 1,
        },
        category: {
          include: {
            collection: {
              include: {
                i18n: {
                  where: { locale: 'fr' },
                  take: 1,
                },
              },
            },
            i18n: {
              where: { locale: 'fr' },
              take: 1,
            },
          },
        },
      },
    })

    return NextResponse.json({ articles })
  } catch (error) {
    console.error('Error fetching articles:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// POST /api/admin/help/articles
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = createArticleSchema.parse(body)

    // Check if article with this slug already exists in this category
    const existing = await prisma.helpArticle.findUnique({
      where: {
        categoryId_slug: {
          categoryId: validated.categoryId,
          slug: validated.slug,
        },
      },
    })

    if (existing) {
      return NextResponse.json(
        { error: 'Article with this slug already exists in this category' },
        { status: 409 }
      )
    }

    const article = await prisma.helpArticle.create({
      data: {
        categoryId: validated.categoryId,
        slug: validated.slug,
        status: 'DRAFT',
        i18n: {
          create: {
            locale: defaultLocale,
            title: validated.title,
            translationStatus: TranslationStatus.ORIGINAL,
          },
        },
      },
      include: {
        i18n: true,
      },
    })

    return NextResponse.json({ article })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Error creating article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

