import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault } from '@/config/locales'
import { cookies } from 'next/headers'
import { ContentStatus } from '@prisma/client'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection: string }> }
) {
  try {
    const { collection } = await params
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale')
    const cookieStore = await cookies()
    const locale = localeParam || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

    const foundCollection = await prisma.helpCollection.findUnique({
      where: { slug: collection },
      include: {
        i18n: { where: { locale }, take: 1 },
        categories: {
          where: { isPublished: true },
          orderBy: { order: 'asc' },
          include: {
            i18n: true,
            articles: {
              where: { status: ContentStatus.PUBLISHED },
              select: { id: true },
            },
          },
        },
      },
    })

    if (!foundCollection || !foundCollection.isPublished) {
      return NextResponse.json({ error: 'Collection not found', categories: [] }, { status: 404 })
    }

    const collectionI18n = foundCollection.i18n[0]
    const pickI18n = <T extends { locale: string }>(rows: T[]) =>
      rows.find((row) => row.locale === locale) ??
      rows.find((row) => row.locale === 'fr') ??
      rows.find((row) => row.locale === 'en') ??
      rows[0]

    const categories = foundCollection.categories.map((category) => {
      const i18n = pickI18n(category.i18n || [])
      return {
        id: category.id,
        slug: category.slug,
        order: category.order,
        title: i18n?.title?.trim() || category.slug,
        description: i18n?.description ?? null,
        articleCount: category.articles.length,
      }
    })

    return NextResponse.json({
      collection: {
        slug: foundCollection.slug,
        title: collectionI18n?.title || foundCollection.slug,
      },
      categories,
    })
  } catch (error) {
    console.error('[Help Categories API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', categories: [] },
      { status: 500 }
    )
  }
}
