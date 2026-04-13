import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { translateSectionData } from '@/lib/translate/translateSectionData'
import { getGlossary } from '@/lib/translate/getGlossary'
import { ContentStatus, TranslationEntityType, TranslationLogStatus, TranslationStatus } from '@prisma/client'
import { supportedLocales, isValidLocale } from '@/config/locales'
import { OPENAI_MODEL } from '@/lib/openai/client'

const translateSectionSchema = z.object({
  sectionContentId: z.string().min(1),
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
    const { sectionContentId, sourceLocale, targetLocales, mode } = translateSectionSchema.parse(body)

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

    // Get source content
    const sourceContent = await prisma.sectionContent.findUnique({
      where: { id: sectionContentId },
      include: { section: true },
    })

    if (!sourceContent) {
      return NextResponse.json({ error: 'Section content not found' }, { status: 404 })
    }

    if (sourceContent.locale !== sourceLocale) {
      return NextResponse.json(
        { error: 'Source locale mismatch' },
        { status: 400 }
      )
    }

    // Get glossary
    const glossary = await getGlossary()

    const results = {
      created: [] as string[],
      updated: [] as string[],
      skipped: [] as string[],
      errors: [] as Array<{ locale: string; error: string }>,
    }

    // Translate to each target locale
    for (const targetLocale of targetLocales) {
      if (targetLocale === sourceLocale) {
        results.skipped.push(targetLocale)
        continue
      }

      try {
        // Check if target already exists
        const existing = await prisma.sectionContent.findUnique({
          where: {
            sectionId_locale_status: {
              sectionId: sourceContent.sectionId,
              locale: targetLocale,
              status: sourceContent.status,
            },
          },
        })

        if (existing && mode === 'missing') {
          results.skipped.push(targetLocale)
          // Log skipped
          await prisma.translationLog.create({
            data: {
              entityType: TranslationEntityType.SECTION,
              entityId: sourceContent.sectionId,
              sourceLocale,
              targetLocale,
              mode,
              status: TranslationLogStatus.SKIPPED,
              model: OPENAI_MODEL,
            },
          })
          continue
        }

        // Translate the data (deep clone is handled inside translateSectionData)
        const translatedData = await translateSectionData(
          sourceContent.data,
          sourceContent.section.key,
          {
            sourceLocale,
            targetLocale,
            glossary: glossary || undefined,
          }
        )

        // Log translation preview (dev only)
        if (process.env.NODE_ENV !== 'production') {
          const preview = JSON.stringify(translatedData).substring(0, 80)
          console.log(
            `[Translate][SECTION][${sourceContent.sectionId}] source=${sourceLocale} target=${targetLocale} preview=${preview}...`
          )
        }

        // Upsert target content with MACHINE status
        // CRITICAL: Ensure locale is correctly set in where clause to prevent mixing
        const upsertResult = await prisma.sectionContent.upsert({
          where: {
            sectionId_locale_status: {
              sectionId: sourceContent.sectionId,
              locale: targetLocale, // ✅ Explicitly set target locale
              status: sourceContent.status,
            },
          },
          create: {
            sectionId: sourceContent.sectionId,
            locale: targetLocale, // ✅ Explicitly set target locale
            status: sourceContent.status,
            data: translatedData,
            translationStatus: TranslationStatus.MACHINE,
            updatedByUserId: session.userId,
          },
          update: {
            data: translatedData,
            translationStatus: TranslationStatus.MACHINE, // Mark as machine-translated
            updatedByUserId: session.userId,
          },
        })

        // Verify the write (dev only)
        if (process.env.NODE_ENV !== 'production') {
          const verify = await prisma.sectionContent.findUnique({
            where: {
              sectionId_locale_status: {
                sectionId: sourceContent.sectionId,
                locale: targetLocale,
                status: sourceContent.status,
              },
            },
          })
          if (verify && verify.locale !== targetLocale) {
            console.error(
              `[Translate][SECTION] ERROR: Written locale mismatch! Expected ${targetLocale}, got ${verify.locale}`
            )
          }
        }

        // Log success
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.SECTION,
            entityId: sourceContent.sectionId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.SUCCESS,
            model: OPENAI_MODEL,
          },
        })

        if (existing) {
          results.updated.push(targetLocale)
        } else {
          results.created.push(targetLocale)
        }
      } catch (error: any) {
        console.error(`Error translating to ${targetLocale}:`, error)
        const errorMessage = error.message || 'Translation failed'
        results.errors.push({
          locale: targetLocale,
          error: errorMessage,
        })

        // Log error (sanitize message to avoid storing sensitive data)
        const sanitizedError = errorMessage.length > 500 ? errorMessage.substring(0, 500) : errorMessage
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.SECTION,
            entityId: sourceContent.sectionId,
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
        { status: 400 }
      )
    }
    console.error('Error in translate section:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

