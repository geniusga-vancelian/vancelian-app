import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { translateText } from '@/lib/translate/translateText'
import { getGlossary } from '@/lib/translate/getGlossary'
import { TranslationEntityType, TranslationLogStatus, TranslationStatus } from '@prisma/client'
import { isValidLocale } from '@/config/locales'
import { OPENAI_MODEL } from '@/lib/openai/client'

/**
 * Auto-traduction d'une AcademyCollection (clone de la route Help). Crée ou
 * met à jour les `AcademyCollectionI18n` pour les locales cibles avec
 * `translationStatus = MACHINE`. Mode `missing` ignore les locales déjà
 * traduites ; `force` les remplace.
 */
const translateCollectionSchema = z.object({
  collectionId: z.string().min(1),
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
    const { collectionId, sourceLocale, targetLocales, mode } =
      translateCollectionSchema.parse(body)

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

    const collection = await prisma.academyCollection.findUnique({
      where: { id: collectionId },
      include: {
        i18n: {
          where: { locale: sourceLocale },
          take: 1,
        },
      },
    })

    if (!collection) {
      return NextResponse.json({ error: 'Collection not found' }, { status: 404 })
    }

    const sourceI18n = collection.i18n[0]
    if (!sourceI18n) {
      return NextResponse.json(
        { error: 'Source locale content not found' },
        { status: 404 },
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
        const existing = await prisma.academyCollectionI18n.findUnique({
          where: {
            collectionId_locale: {
              collectionId,
              locale: targetLocale,
            },
          },
        })

        if (existing && mode === 'missing') {
          results.skipped.push(targetLocale)
          await prisma.translationLog.create({
            data: {
              entityType: TranslationEntityType.ACADEMY_COLLECTION,
              entityId: collectionId,
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

        const subtitleResult = sourceI18n.subtitle
          ? await translateText(sourceI18n.subtitle, {
              sourceLocale,
              targetLocale,
              glossary: glossary || undefined,
            })
          : null

        const descriptionResult = sourceI18n.description
          ? await translateText(sourceI18n.description, {
              sourceLocale,
              targetLocale,
              glossary: glossary || undefined,
            })
          : null

        await prisma.academyCollectionI18n.upsert({
          where: {
            collectionId_locale: {
              collectionId,
              locale: targetLocale,
            },
          },
          create: {
            collectionId,
            locale: targetLocale,
            title: titleResult.translated,
            subtitle: subtitleResult?.translated || null,
            description: descriptionResult?.translated || null,
            translationStatus: TranslationStatus.MACHINE,
          },
          update: {
            title: titleResult.translated,
            subtitle: subtitleResult?.translated || null,
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
            entityType: TranslationEntityType.ACADEMY_COLLECTION,
            entityId: collectionId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.SUCCESS,
            model: OPENAI_MODEL,
          },
        })
      } catch (error) {
        const err = error as Error
        console.error(`Error translating academy collection to ${targetLocale}:`, err)
        results.errors.push({
          locale: targetLocale,
          error: err.message || 'Translation failed',
        })

        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.ACADEMY_COLLECTION,
            entityId: collectionId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.ERROR,
            model: OPENAI_MODEL,
            errorMessage: err.message || 'Translation failed',
          },
        })
      }
    }

    return NextResponse.json({ results })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 },
      )
    }
    console.error('Error translating academy collection:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
