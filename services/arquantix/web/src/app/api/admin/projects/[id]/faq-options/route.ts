import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { defaultLocale, getLocaleOrDefault } from '@/config/locales'

type FaqOptionRow = {
  id: string
  slug: string
  question: string
  standfirst: string | null
  collection_slug: string
  category_slug: string
}

// GET /api/admin/projects/[id]/faq-options?locale=fr
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
    const locale = getLocaleOrDefault(searchParams.get('locale') || defaultLocale)
    const projectId = params.id

    const rows = await prisma.$queryRawUnsafe<FaqOptionRow[]>(
      `
      SELECT
        ha."id",
        ha."slug",
        COALESCE(hai_locale."title", hai_default."title", ha."slug") AS "question",
        COALESCE(hai_locale."standfirst", hai_default."standfirst") AS "standfirst",
        hc2."slug" AS "collection_slug",
        hc."slug" AS "category_slug"
      FROM "help_articles" ha
      INNER JOIN "help_categories" hc ON hc."id" = ha."category_id" AND hc."is_published" = true
      INNER JOIN "help_collections" hc2 ON hc2."id" = hc."collection_id" AND hc2."is_published" = true
      LEFT JOIN "help_article_i18n" hai_locale ON hai_locale."article_id" = ha."id" AND hai_locale."locale" = $1
      LEFT JOIN "help_article_i18n" hai_default ON hai_default."article_id" = ha."id" AND hai_default."locale" = $2
      WHERE ha."status" = 'PUBLISHED'
        AND ha."target_tags" @> $3::jsonb
      ORDER BY ha."updated_at" DESC
      `,
      locale,
      defaultLocale,
      JSON.stringify([{ type: 'EXCLUSIVE_OFFER', id: projectId }])
    )

    return NextResponse.json({
      options: rows.map((row) => ({
        articleId: row.id,
        articleSlug: row.slug,
        question: row.question,
        standfirst: row.standfirst ?? '',
        collectionSlug: row.collection_slug,
        categorySlug: row.category_slug,
      })),
    })
  } catch (error) {
    console.error('[Project FAQ options API] Error:', error)
    return NextResponse.json({ error: 'Internal server error', options: [] }, { status: 500 })
  }
}
