import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { translateText } from '@/lib/translate/translateText'
import { getGlossary } from '@/lib/translate/getGlossary'
import { isValidLocale } from '@/config/locales'
import { TranslationEntityType, TranslationLogStatus, TranslationStatus } from '@prisma/client'
import { OPENAI_MODEL } from '@/lib/openai/client'

const translateMenuSchema = z.object({
  menuId: z.string().min(1),
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
    const { menuId, sourceLocale, targetLocales, mode } = translateMenuSchema.parse(body)

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

    // Fetch menu
    const menu = await prisma.menu.findUnique({
      where: { id: menuId },
    })

    if (!menu) {
      return NextResponse.json({ error: 'Menu not found' }, { status: 404 })
    }

    // Fetch source i18n
    const sourceI18n = await prisma.menuI18n.findUnique({
      where: {
        menuId_locale: {
          menuId,
          locale: sourceLocale,
        },
      },
    })

    if (!sourceI18n) {
      return NextResponse.json(
        { error: `Source name not found for locale: ${sourceLocale}` },
        { status: 404 }
      )
    }

    if (!sourceI18n.name || sourceI18n.name.trim().length === 0) {
      return NextResponse.json(
        { error: 'Source name is empty' },
        { status: 400 }
      )
    }

    // Get glossary
    const glossary = await getGlossary()

    // Translate for each target locale
    const results: Array<{ locale: string; status: 'success' | 'error' | 'skipped'; error?: string }> = []

    for (const targetLocale of targetLocales) {
      try {
        // Check if translation already exists
        const existing = await prisma.menuI18n.findUnique({
          where: {
            menuId_locale: {
              menuId,
              locale: targetLocale,
            },
          },
        })

        if (existing && mode === 'missing') {
          results.push({ locale: targetLocale, status: 'skipped' })
          continue
        }

        // Translate name
        const translationResult = await translateText(sourceI18n.name, {
          sourceLocale,
          targetLocale,
          glossary: glossary || undefined,
        })
        const translatedName = translationResult.translated

        // Upsert i18n
        await prisma.menuI18n.upsert({
          where: {
            menuId_locale: {
              menuId,
              locale: targetLocale,
            },
          },
          create: {
            menuId,
            locale: targetLocale,
            name: translatedName,
            translationStatus: TranslationStatus.MACHINE,
          },
          update: {
            name: translatedName,
            translationStatus: TranslationStatus.MACHINE,
          },
        })

        // Log success
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.MENU,
            entityId: menuId,
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
        console.error(`Error translating menu to ${targetLocale}:`, error)

        // Log error
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.MENU,
            entityId: menuId,
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
    console.error('Error translating menu:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

