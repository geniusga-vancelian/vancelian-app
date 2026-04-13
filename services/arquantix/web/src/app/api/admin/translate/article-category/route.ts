import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { translateText } from '@/lib/translate/translateText'
import { getGlossary } from '@/lib/translate/getGlossary'
import { isValidLocale } from '@/config/locales'
import { TranslationEntityType, TranslationLogStatus, TranslationStatus } from '@prisma/client'
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
    console.log('[Translate Category] Request body:', JSON.stringify(body, null, 2))
    const { categoryId, sourceLocale, targetLocales, mode } = translateCategorySchema.parse(body)
    console.log('[Translate Category] Parsed:', { categoryId, sourceLocale, targetLocales, mode })

    // Validate: sourceLocale must not be in targetLocales
    if (targetLocales.includes(sourceLocale)) {
      return NextResponse.json(
        { error: 'Source locale cannot be in target locales' },
        { status: 400 }
      )
    }

    // Validate: targetLocales must be distinct
    if (new Set(targetLocales).size !== targetLocales.length) {
      return NextResponse.json(
        { error: 'Target locales must be distinct' },
        { status: 400 }
      )
    }

    // Fetch category
    console.log('[Translate Category] Fetching category:', categoryId)
    const category = await prisma.articleCategory.findUnique({
      where: { id: categoryId },
    })

    if (!category) {
      console.error('[Translate Category] Category not found:', categoryId)
      return NextResponse.json({ error: 'Category not found' }, { status: 404 })
    }
    console.log('[Translate Category] Category found:', { id: category.id, label: category.label })

    // Fetch source i18n or use base label
    let sourceLabel: string
    
    console.log('[Translate Category] Fetching source i18n:', { categoryId, sourceLocale })
    const sourceI18n = await prisma.articleCategoryI18n.findUnique({
      where: {
        categoryId_locale: {
          categoryId: categoryId,
          locale: sourceLocale,
        },
      },
    })
    console.log('[Translate Category] Source i18n:', sourceI18n ? { label: sourceI18n.label } : 'not found')

    if (sourceI18n && sourceI18n.label && sourceI18n.label.trim().length > 0) {
      sourceLabel = sourceI18n.label
      console.log('[Translate Category] Using i18n label:', sourceLabel)
    } else if (category.label && category.label.trim().length > 0) {
      // Fallback to base label if i18n doesn't exist
      sourceLabel = category.label
      console.log('[Translate Category] Using base label as fallback:', sourceLabel)
    } else {
      console.error('[Translate Category] No source label available')
      return NextResponse.json(
        { error: `Source label not found for locale: ${sourceLocale} and no base label available` },
        { status: 404 }
      )
    }

    // Get glossary
    console.log('[Translate Category] Fetching glossary...')
    const glossary = await getGlossary()
    console.log('[Translate Category] Glossary fetched:', glossary ? 'OK' : 'empty')

    // Translate for each target locale
    const results: Array<{ locale: string; status: 'success' | 'error' | 'skipped'; error?: string }> = []

    for (const targetLocale of targetLocales) {
      try {
        console.log(`[Translate Category] Processing target locale: ${targetLocale}`)
        // Check if translation already exists
        const existing = await prisma.articleCategoryI18n.findUnique({
          where: {
            categoryId_locale: {
              categoryId: categoryId,
              locale: targetLocale,
            },
          },
        })

        if (existing && mode === 'missing') {
          console.log(`[Translate Category] Skipping ${targetLocale} (already exists)`)
          results.push({ locale: targetLocale, status: 'skipped' })
          continue
        }

        // Translate label
        console.log(`[Translate Category] Translating to ${targetLocale}...`)
        const translationResult = await translateText(sourceLabel, {
          sourceLocale,
          targetLocale,
          glossary: glossary || undefined,
        })
        const translatedLabel = translationResult.translated
        console.log(`[Translate Category] Translated label for ${targetLocale}:`, translatedLabel.substring(0, 50) + '...')

        // Upsert i18n
        console.log(`[Translate Category] Upserting i18n for ${targetLocale}...`)
        try {
          await prisma.articleCategoryI18n.upsert({
            where: {
              categoryId_locale: {
                categoryId: categoryId,
                locale: targetLocale,
              },
            },
            create: {
              categoryId: categoryId,
              locale: targetLocale,
              label: translatedLabel,
              translationStatus: TranslationStatus.MACHINE,
            },
            update: {
              label: translatedLabel,
              translationStatus: TranslationStatus.MACHINE,
            },
          })
          console.log(`[Translate Category] Successfully upserted i18n for ${targetLocale}`)
        } catch (upsertError: any) {
          console.error(`[Translate Category] Prisma upsert error for category ${categoryId}, locale ${targetLocale}:`, {
            message: upsertError?.message,
            code: upsertError?.code,
            meta: upsertError?.meta,
            stack: upsertError?.stack,
          })
          throw upsertError
        }

        // Log success
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.ARTICLE_CATEGORY,
            entityId: categoryId,
            sourceLocale: sourceLocale,
            targetLocale: targetLocale,
            mode,
            status: TranslationLogStatus.SUCCESS,
            model: OPENAI_MODEL,
          },
        })

        results.push({ locale: targetLocale, status: 'success' })
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error'
        console.error(`Error translating category to ${targetLocale}:`, error)

        // Log error
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.ARTICLE_CATEGORY,
            entityId: categoryId,
            sourceLocale: sourceLocale,
            targetLocale: targetLocale,
            mode,
            status: TranslationLogStatus.ERROR,
            errorMessage: errorMessage,
            model: OPENAI_MODEL,
          },
        })

        results.push({ locale: targetLocale, status: 'error', error: errorMessage })
      }
    }

    const successCount = results.filter((r) => r.status === 'success').length
    const errorCount = results.filter((r) => r.status === 'error').length
    const skippedCount = results.filter((r) => r.status === 'skipped').length

    // Format response to match TranslateModal expectations
    const created: string[] = []
    const updated: string[] = []
    const skipped: string[] = []
    const errors: Array<{ locale: string; error: string }> = []

    results.forEach((r) => {
      if (r.status === 'success') {
        updated.push(r.locale)
      } else if (r.status === 'skipped') {
        skipped.push(r.locale)
      } else if (r.status === 'error') {
        errors.push({ locale: r.locale, error: r.error || 'Unknown error' })
      }
    })

    return NextResponse.json({
      message: 'Translation completed',
      results: {
        created,
        updated,
        skipped,
        errors,
      },
      summary: {
        total: targetLocales.length,
        success: successCount,
        error: errorCount,
        skipped: skippedCount,
      },
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error translating category:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    const errorStack = error instanceof Error ? error.stack : undefined
    return NextResponse.json(
      { 
        error: 'Internal server error',
        message: errorMessage,
        ...(process.env.NODE_ENV === 'development' && { stack: errorStack })
      },
      { status: 500 }
    )
  }
}

