import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { getGlossary } from '@/lib/translate/getGlossary'
import { isValidLocale } from '@/config/locales'
import { TranslationEntityType, TranslationLogStatus } from '@prisma/client'
import { OPENAI_MODEL } from '@/lib/openai/client'
import { translateArticleToTargetLocale } from '@/lib/translate/translateArticleToTargetLocale'

const translateArticleSchema = z.object({
  articleId: z.string().min(1),
  sourceLocale: z.string().refine(isValidLocale, { message: 'Invalid source locale' }),
  targetLocales: z
    .array(z.string().refine(isValidLocale, { message: 'Invalid target locale' }))
    .min(1)
    .max(10),
  mode: z.enum(['missing', 'force']).default('missing'),
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { articleId, sourceLocale, targetLocales, mode } = translateArticleSchema.parse(body)

    if (targetLocales.includes(sourceLocale)) {
      return NextResponse.json(
        { error: 'Source locale cannot be in target locales' },
        { status: 400 },
      )
    }

    if (new Set(targetLocales).size !== targetLocales.length) {
      return NextResponse.json(
        { error: 'Target locales must be distinct' },
        { status: 400 },
      )
    }

    const sourceI18n = await prisma.articleI18n.findUnique({
      where: {
        articleId_locale: {
          articleId,
          locale: sourceLocale,
        },
      },
    })

    if (!sourceI18n) {
      return NextResponse.json({ error: 'Source article i18n not found' }, { status: 404 })
    }

    const sourceBlocks = await prisma.articleBlock.findMany({
      where: { articleId },
      orderBy: { order: 'asc' },
    })

    const glossary = await getGlossary()

    const results = {
      created: [] as string[],
      updated: [] as string[],
      skipped: [] as string[],
      errors: [] as Array<{ locale: string; error: string }>,
    }

    for (const targetLocale of targetLocales) {
      if (targetLocale === sourceLocale) {
        results.skipped.push(targetLocale)
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.ARTICLE,
            entityId: articleId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.SKIPPED,
            model: OPENAI_MODEL,
          },
        })
        continue
      }

      try {
        const r = await translateArticleToTargetLocale({
          prisma,
          articleId,
          sourceLocale,
          targetLocale,
          mode,
          sourceI18n,
          sourceBlocks,
          glossary,
        })
        if (r.kind === 'skipped') {
          results.skipped.push(targetLocale)
        } else {
          if (r.wasUpdate) {
            results.updated.push(targetLocale)
          } else {
            results.created.push(targetLocale)
          }
        }
      } catch (error: any) {
        console.error(`Error translating article to ${targetLocale}:`, error)
        const errorMessage = error?.message || 'Translation failed'
        results.errors.push({
          locale: targetLocale,
          error: errorMessage,
        })
        const sanitizedError = errorMessage.length > 500 ? errorMessage.substring(0, 500) : errorMessage
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.ARTICLE,
            entityId: articleId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.ERROR,
            model: OPENAI_MODEL,
            errorMessage: sanitizedError,
          },
        })
      }
    }

    return NextResponse.json({ results })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 },
      )
    }
    console.error('Error in translate article:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
