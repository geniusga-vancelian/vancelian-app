import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { isValidLocale } from '@/config/locales'

const updateI18nSchema = z.object({
  locale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
  title: z.string().min(1),
  standfirst: z.string().optional().nullable(),
  contentMarkdown: z.string().optional().nullable(),
  metaTitle: z.string().optional().nullable(),
  metaDescription: z.string().optional().nullable(),
})

// PUT /api/admin/help/articles/[id]/i18n
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
    const validated = updateI18nSchema.parse(body)

    let i18n: any
    try {
      i18n = await prisma.helpArticleI18n.upsert({
        where: {
          articleId_locale: {
            articleId: params.id,
            locale: validated.locale,
          },
        },
        update: {
          title: validated.title,
          standfirst: validated.standfirst,
          contentMarkdown: validated.contentMarkdown,
          metaTitle: validated.metaTitle,
          metaDescription: validated.metaDescription,
        },
        create: {
          articleId: params.id,
          locale: validated.locale,
          title: validated.title,
          standfirst: validated.standfirst,
          contentMarkdown: validated.contentMarkdown,
          metaTitle: validated.metaTitle,
          metaDescription: validated.metaDescription,
          translationStatus: 'ORIGINAL',
        },
      })
    } catch (err: any) {
      // Backward-compatible path when Prisma runtime client is older than schema.
      // In that case, persist classic fields with Prisma and markdown with raw SQL.
      const message = typeof err?.message === 'string' ? err.message : ''
      if (!message.includes('Unknown argument `contentMarkdown`')) {
        throw err
      }

      i18n = await prisma.helpArticleI18n.upsert({
        where: {
          articleId_locale: {
            articleId: params.id,
            locale: validated.locale,
          },
        },
        update: {
          title: validated.title,
          standfirst: validated.standfirst,
          metaTitle: validated.metaTitle,
          metaDescription: validated.metaDescription,
        },
        create: {
          articleId: params.id,
          locale: validated.locale,
          title: validated.title,
          standfirst: validated.standfirst,
          metaTitle: validated.metaTitle,
          metaDescription: validated.metaDescription,
          translationStatus: 'ORIGINAL',
        },
      })

      await prisma.$executeRaw`
        UPDATE "help_article_i18n"
        SET "content_markdown" = ${validated.contentMarkdown ?? null}
        WHERE "article_id" = ${params.id} AND "locale" = ${validated.locale}
      `
    }

    return NextResponse.json({ i18n })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating article i18n:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









