import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { cookies } from 'next/headers'
import { defaultLocale, getLocaleOrDefault } from '@/config/locales'

type TaggedHelpRow = {
  id: string
  slug: string
  question: string
  standfirst: string | null
  collection_slug: string
  collection_title: string
  category_slug: string
  category_title: string
  updated_at: Date
}

// GET /api/help/articles/by-tag?type=EXCLUSIVE_OFFER&id=<projectId>&locale=fr
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const type = (searchParams.get('type') || '').trim().toUpperCase()
    const id = (searchParams.get('id') || '').trim()
    const localeParam = searchParams.get('locale')

    if (!type || !id) {
      return NextResponse.json({ error: 'Missing tag type or id', articles: [] }, { status: 400 })
    }

    const cookieStore = await cookies()
    const locale = getLocaleOrDefault(localeParam || cookieStore.get('arquantix-locale')?.value || defaultLocale)

    const rows = await prisma.$queryRawUnsafe<TaggedHelpRow[]>(
      `
      SELECT
        ha."id",
        ha."slug",
        COALESCE(hai_locale."title", hai_default."title", ha."slug") AS "question",
        COALESCE(hai_locale."standfirst", hai_default."standfirst") AS "standfirst",
        hc2."slug" AS "collection_slug",
        COALESCE(hc2i_locale."title", hc2i_default."title", hc2."slug") AS "collection_title",
        hc."slug" AS "category_slug",
        COALESCE(hci_locale."title", hci_default."title", hc."slug") AS "category_title",
        ha."updated_at"
      FROM "help_articles" ha
      INNER JOIN "help_categories" hc ON hc."id" = ha."category_id" AND hc."is_published" = true
      INNER JOIN "help_collections" hc2 ON hc2."id" = hc."collection_id" AND hc2."is_published" = true
      LEFT JOIN "help_article_i18n" hai_locale ON hai_locale."article_id" = ha."id" AND hai_locale."locale" = $1
      LEFT JOIN "help_article_i18n" hai_default ON hai_default."article_id" = ha."id" AND hai_default."locale" = $2
      LEFT JOIN "help_category_i18n" hci_locale ON hci_locale."category_id" = hc."id" AND hci_locale."locale" = $1
      LEFT JOIN "help_category_i18n" hci_default ON hci_default."category_id" = hc."id" AND hci_default."locale" = $2
      LEFT JOIN "help_collection_i18n" hc2i_locale ON hc2i_locale."collection_id" = hc2."id" AND hc2i_locale."locale" = $1
      LEFT JOIN "help_collection_i18n" hc2i_default ON hc2i_default."collection_id" = hc2."id" AND hc2i_default."locale" = $2
      WHERE ha."status" = 'PUBLISHED'
        AND ha."target_tags" @> $3::jsonb
      ORDER BY ha."updated_at" DESC
      `,
      locale,
      defaultLocale,
      JSON.stringify([{ type, id }])
    )

    return NextResponse.json({
      tag: { type, id },
      articles: rows.map((row) => ({
        id: row.id,
        slug: row.slug,
        question: row.question,
        standfirst: row.standfirst ?? null,
        collection: {
          slug: row.collection_slug,
          title: row.collection_title,
        },
        category: {
          slug: row.category_slug,
          title: row.category_title,
        },
        updatedAt: row.updated_at,
      })),
    })
  } catch (error) {
    console.error('[Help by tag API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', articles: [] },
      { status: 500 }
    )
  }
}
