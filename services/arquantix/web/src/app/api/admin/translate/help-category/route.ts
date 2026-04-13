import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { translateText } from '@/lib/translate/translateText'
import { getGlossary } from '@/lib/translate/getGlossary'
import { TranslationEntityType, TranslationLogStatus, TranslationStatus } from '@prisma/client'
import { supportedLocales, isValidLocale } from '@/config/locales'
import { OPENAI_MODEL } from '@/lib/openai/client'

const translateCategorySchema = z.object({
  categoryId: z.string().min(1),
  sourceLocale: z.string().refine(isValidLocale, { message: 'Invalid source locale' }),
  targetLocales: z.array(z.string().refine(isValidLocale, { message: 'Invalid target locale' })).min(1).max(10),
  mode: z.enum(['missing', 'force']).default('missing'),
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { categoryId, sourceLocale, targetLocales, mode } = translateCategorySchema.parse(body)

    if (targetLocales.includes(sourceLocale)) {
      return NextResponse.json(
        { error: 'Source locale cannot be in target locales' },
        { status: 400 }
      )
    }

    if (new Set(targetLocales).size !== targetLocales.length) {
      return NextResponse.json(
        { error: 'Target locales must be distinct' },
        { status: 400 }
      )
    }

    const category = await prisma.helpCategory.findUnique({
      where: { id: categoryId },
      include: {
        i18n: {
          where: { locale: sourceLocale },
          take: 1,
        },
      },
    })

    if (!category) {
      return NextResponse.json({ error: 'Category not found' }, { status: 404 })
    }

    const sourceI18n = category.i18n[0]
    if (!sourceI18n) {
      return NextResponse.json(
        { error: 'Source locale content not found' },
        { status: 404 }
      )
    }

    const glossary = await getGlossary()

    const results = {
      created: [] as string[],
      updated: [] as string[],
      skipped: [] as string[],
      errors: [] as Array<{ locale: string; error: string }>,
    }

    for (const targetLocale of targetLocales) {
      try {
        const existing = await prisma.helpCategoryI18n.findUnique({
          where: {
            categoryId_locale: {
              categoryId,
              locale: targetLocale,
            },
          },
        })

        if (existing && mode === 'missing') {
          results.skipped.push(targetLocale)
          await prisma.translationLog.create({
            data: {
              entityType: TranslationEntityType.HELP_CATEGORY,
              entityId: categoryId,
              sourceLocale,
              targetLocale,
              mode,
              status: TranslationLogStatus.SKIPPED,
              model: OPENAI_MODEL,
            },
          })
          continue
        }

        const titleResult = await translateText(sourceI18n.title, {
          sourceLocale,
          targetLocale,
          glossary: glossary || undefined,
        })

        const descriptionResult = sourceI18n.description
          ? await translateText(sourceI18n.description, {
              sourceLocale,
              targetLocale,
              glossary: glossary || undefined,
            })
          : null

        const i18n = await prisma.helpCategoryI18n.upsert({
          where: {
            categoryId_locale: {
              categoryId,
              locale: targetLocale,
            },
          },
          create: {
            categoryId,
            locale: targetLocale,
            title: titleResult.translated,
            description: descriptionResult?.translated || null,
            translationStatus: TranslationStatus.MACHINE,
          },
          update: {
            title: titleResult.translated,
            description: descriptionResult?.translated || null,
            translationStatus: TranslationStatus.MACHINE,
          },
        })

        if (existing) {
          results.updated.push(targetLocale)
        } else {
          results.created.push(targetLocale)
        }

        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.HELP_CATEGORY,
            entityId: categoryId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.SUCCESS,
            model: OPENAI_MODEL,
          },
        })
      } catch (error: any) {
        console.error(`Error translating category to ${targetLocale}:`, error)
        results.errors.push({
          locale: targetLocale,
          error: error.message || 'Translation failed',
        })

        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.HELP_CATEGORY,
            entityId: categoryId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.ERROR,
            model: OPENAI_MODEL,
            errorMessage: error.message || 'Translation failed',
          },
        })
      }
    }

    return NextResponse.json({ results })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Error translating category:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









