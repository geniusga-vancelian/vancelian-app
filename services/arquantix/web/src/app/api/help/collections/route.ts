import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault } from '@/config/locales'
import { cookies } from 'next/headers'
import { ContentStatus } from '@prisma/client'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale')
    const cookieStore = await cookies()
    const locale = localeParam || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

    const collections = await prisma.helpCollection.findMany({
      where: { isPublished: true },
      orderBy: { order: 'asc' },
      include: {
        i18n: { where: { locale }, take: 1 },
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

    const payload = collections
      .map((collection) => {
        const i18n = collection.i18n[0]
        if (!i18n) return null
        const articleCount = collection.categories.reduce((sum, cat) => sum + cat.articles.length, 0)
        return {
          id: collection.id,
          slug: collection.slug,
          iconKey: collection.iconKey,
          colorHex: collection.colorHex,
          order: collection.order,
          title: i18n.title,
          subtitle: i18n.subtitle ?? null,
          description: i18n.description ?? null,
          articleCount,
        }
      })
      .filter((item): item is NonNullable<typeof item> => item !== null)

    return NextResponse.json({ collections: payload })
  } catch (error) {
    console.error('[Help Collections API] Error:', error)
    return NextResponse.json({ error: 'Internal server error', collections: [] }, { status: 500 })
  }
}
