import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { defaultLocale, isValidLocale } from '@/config/locales'
import { awaitRouteParams } from '@/lib/api/routeParams'

const updateI18nSchema = z.object({
  locale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
  title: z.string().min(1, { message: 'Title is required' }),
  // Standfirst optionnel : la chaîne vide est acceptée. La colonne DB
  // (`ArticleI18n.standfirst`) reste `String NOT NULL` ; on stocke `''`
  // lorsque l'éditeur ne saisit rien (aucun consommateur ne casse, tous
  // gèrent déjà le cas via `?? ''` / `|| ''`).
  standfirst: z.string().optional().default(''),
  coverTitle: z.string().optional().nullable(),
  metaTitle: z.string().optional().nullable(),
  metaDescription: z.string().optional().nullable(),
  seoJson: z.record(z.string(), z.unknown()).optional(),
})

// PUT /api/admin/articles/[id]/i18n
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } | Promise<{ id: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id: articleId } = await awaitRouteParams(params)

    const body = await request.json()
    const validated = updateI18nSchema.parse(body)

    // Normalize optional fields
    const normalizedCoverTitle = validated.coverTitle === '' || validated.coverTitle === undefined ? null : validated.coverTitle
    const normalizedMetaTitle = validated.metaTitle === '' || validated.metaTitle === undefined ? null : validated.metaTitle
    const normalizedMetaDescription = validated.metaDescription === '' || validated.metaDescription === undefined ? null : validated.metaDescription
    const seoJsonPayload =
      validated.seoJson !== undefined
        ? (JSON.parse(JSON.stringify(validated.seoJson)) as object)
        : undefined

    // Upsert i18n
    const i18n = await prisma.articleI18n.upsert({
      where: {
        articleId_locale: {
          articleId: articleId,
          locale: validated.locale,
        },
      },
      update: {
        title: validated.title,
        standfirst: validated.standfirst,
        coverTitle: normalizedCoverTitle,
        metaTitle: normalizedMetaTitle,
        metaDescription: normalizedMetaDescription,
        ...(seoJsonPayload !== undefined ? { seoJson: seoJsonPayload } : {}),
      },
      create: {
        articleId: articleId,
        locale: validated.locale,
        title: validated.title,
        standfirst: validated.standfirst,
        coverTitle: normalizedCoverTitle,
        metaTitle: normalizedMetaTitle,
        metaDescription: normalizedMetaDescription,
        seoJson: seoJsonPayload ?? {},
      },
    })

    if (validated.locale === defaultLocale) {
      await prisma.article.update({
        where: { id: articleId },
        data: { coverTitle: normalizedCoverTitle },
      })
    }

    return NextResponse.json({ i18n })
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('Validation error:', JSON.stringify(error.issues, null, 2))
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating article i18n:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    const errorStack = error instanceof Error ? error.stack : undefined
    console.error('Error details:', { errorMessage, errorStack })
    return NextResponse.json(
      { error: 'Internal server error', details: errorMessage },
      { status: 500 }
    )
  }
}

