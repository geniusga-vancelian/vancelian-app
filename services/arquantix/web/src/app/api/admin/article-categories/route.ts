import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { resolveLabelWithFallback, DEFAULT_LOCALE } from '@/lib/i18n/resolveLabel'
import { getLocaleOrDefault } from '@/config/locales'
import { z } from 'zod'

// GET /api/admin/article-categories
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Get locale from query param, default to fr
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || DEFAULT_LOCALE
    const locale = getLocaleOrDefault(localeParam)

    const categories = await prisma.articleCategory.findMany({
      where: { isActive: true },
      orderBy: [{ order: 'asc' }, { label: 'asc' }],
      include: {
        i18n: true,
      },
    })

    // Resolve labels for requested locale
    const categoriesWithLabels = categories.map((category) => ({
      id: category.id,
      slug: category.slug,
      order: category.order,
      isActive: category.isActive,
      label: resolveLabelWithFallback({
        requestedLocale: locale,
        baseLabel: category.label,
        i18nRows: category.i18n.map((i18n) => ({
          locale: i18n.locale,
          label: i18n.label,
        })),
      }),
      labelBase: category.label, // Keep base label for reference
      i18n: category.i18n, // Include full i18n data for admin UI
    }))

    return NextResponse.json({ categories: categoriesWithLabels })
  } catch (error) {
    console.error('Error fetching article categories:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// POST /api/admin/article-categories - Create a new category
const createCategorySchema = z.object({
  slug: z.string().min(1).max(100).regex(/^[a-z0-9-]+$/, 'Slug must contain only lowercase letters, numbers, and hyphens'),
  label: z.string().min(1).max(200),
  order: z.number().int().default(0),
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { slug, label, order } = createCategorySchema.parse(body)

    // Check if slug already exists
    const existing = await prisma.articleCategory.findUnique({
      where: { slug },
    })

    if (existing) {
      return NextResponse.json(
        { error: 'Category with this slug already exists' },
        { status: 409 }
      )
    }

    // Create category
    const category = await prisma.articleCategory.create({
      data: {
        slug,
        label,
        order,
        isActive: true,
      },
      include: {
        i18n: true,
      },
    })

    // Create default i18n entry for default locale
    await prisma.articleCategoryI18n.create({
      data: {
        categoryId: category.id,
        locale: DEFAULT_LOCALE,
        label,
        translationStatus: 'ORIGINAL',
      },
    })

    return NextResponse.json({ category }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
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

