import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { translateText } from '@/lib/translate/translateText'
import { getGlossary } from '@/lib/translate/getGlossary'
import { isValidLocale } from '@/config/locales'
import { TranslationEntityType, TranslationLogStatus, TranslationStatus } from '@prisma/client'
import { OPENAI_MODEL } from '@/lib/openai/client'

const translateMenuItemSchema = z.object({
  menuItemId: z.string().min(1),
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
    const { menuItemId, sourceLocale, targetLocales, mode } = translateMenuItemSchema.parse(body)

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

    // Fetch menu item
    const menuItem = await prisma.menuItem.findUnique({
      where: { id: menuItemId },
    })

    if (!menuItem) {
      return NextResponse.json({ error: 'Menu item not found' }, { status: 404 })
    }

    // Fetch source i18n
    const sourceI18n = await prisma.menuItemI18n.findUnique({
      where: {
        menuItemId_locale: {
          menuItemId: menuItemId,
          locale: sourceLocale,
        },
      },
    })

    if (!sourceI18n) {
      return NextResponse.json(
        { error: `Source label not found for locale: ${sourceLocale}` },
        { status: 404 }
      )
    }

    if (!sourceI18n.label || sourceI18n.label.trim().length === 0) {
      return NextResponse.json(
        { error: 'Source label is empty' },
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
        const existing = await prisma.menuItemI18n.findUnique({
          where: {
            menuItemId_locale: {
              menuItemId: menuItemId,
              locale: targetLocale,
            },
          },
        })

        if (existing && mode === 'missing') {
          results.push({ locale: targetLocale, status: 'skipped' })
          continue
        }

        // Translate label
        const translationResult = await translateText(sourceI18n.label, {
          sourceLocale,
          targetLocale,
          glossary: glossary || undefined,
        })
        const translatedLabel = translationResult.translated

        // Upsert i18n
        await prisma.menuItemI18n.upsert({
          where: {
            menuItemId_locale: {
              menuItemId: menuItemId,
              locale: targetLocale,
            },
          },
          create: {
            menuItemId: menuItemId,
            locale: targetLocale,
            label: translatedLabel,
            translationStatus: TranslationStatus.MACHINE,
          },
          update: {
            label: translatedLabel,
            translationStatus: TranslationStatus.MACHINE,
          },
        })

        // Log success
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.MENU_ITEM,
            entityId: menuItemId,
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
        console.error(`Error translating menu item to ${targetLocale}:`, error)

        // Log error
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.MENU_ITEM,
            entityId: menuItemId,
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
        // Check if it was created or updated by checking if it existed before
        // For simplicity, we'll mark all as updated (TranslateModal will handle it)
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
    console.error('Error translating menu item:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

