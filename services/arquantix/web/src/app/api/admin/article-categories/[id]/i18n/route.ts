import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { getLocaleOrDefault } from '@/config/locales'

const updateCategoryI18nSchema = z.object({
  locale: z.string().min(1),
  label: z.string().min(1, 'Label is required'),
})

// GET /api/admin/article-categories/[id]/i18n?locale=xx
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
    const localeParam = searchParams.get('locale')
    const locale = localeParam ? getLocaleOrDefault(localeParam) : null

    const category = await prisma.articleCategory.findUnique({
      where: { id: params.id },
      include: {
        i18n: locale
          ? {
              where: { locale },
              take: 1,
            }
          : true,
      },
    })

    if (!category) {
      return NextResponse.json({ error: 'Category not found' }, { status: 404 })
    }

    return NextResponse.json({ i18n: category.i18n })
  } catch (error) {
    console.error('Error fetching category i18n:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// PUT /api/admin/article-categories/[id]/i18n
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { locale, label } = updateCategoryI18nSchema.parse(body)

    // Verify category exists
    const category = await prisma.articleCategory.findUnique({
      where: { id: params.id },
    })

    if (!category) {
      return NextResponse.json({ error: 'Category not found' }, { status: 404 })
    }

    // Upsert i18n row
    const i18n = await prisma.articleCategoryI18n.upsert({
      where: {
        categoryId_locale: {
          categoryId: params.id,
          locale,
        },
      },
      create: {
        categoryId: params.id,
        locale,
        label,
        translationStatus: 'ORIGINAL',
      },
      update: {
        label,
      },
    })

    return NextResponse.json({ i18n })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating category i18n:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

