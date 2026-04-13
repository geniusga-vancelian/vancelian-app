import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { translateText } from '@/lib/translate/translateText'
import { translateMarkdown } from '@/lib/translate/translateMarkdown'
import { getGlossary } from '@/lib/translate/getGlossary'
import { supportedLocales, isValidLocale } from '@/config/locales'
import { TranslationEntityType, TranslationLogStatus, TranslationStatus } from '@prisma/client'
import { OPENAI_MODEL } from '@/lib/openai/client'

const translateArticleSchema = z.object({
  articleId: z.string().min(1),
  sourceLocale: z.string().refine(isValidLocale, { message: 'Invalid source locale' }),
  targetLocales: z.array(z.string().refine(isValidLocale, { message: 'Invalid target locale' })).min(1).max(10),
  mode: z.enum(['missing', 'force']).default('missing'),
})

function truncateMeta(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
}

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
        { status: 400 }
      )
    }

    if (new Set(targetLocales).size !== targetLocales.length) {
      return NextResponse.json(
        { error: 'Target locales must be distinct' },
        { status: 400 }
      )
    }

    const sourceI18n = await prisma.helpArticleI18n.findUnique({
      where: {
        articleId_locale: {
          articleId,
          locale: sourceLocale,
        },
      },
    })

    if (!sourceI18n) {
      return NextResponse.json(
        { error: 'Source article i18n not found' },
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
        const existing = await prisma.helpArticleI18n.findUnique({
          where: {
            articleId_locale: {
              articleId,
              locale: targetLocale,
            },
          },
        })

        // In "missing" mode, check if translation is actually needed
        if (mode === 'missing') {
          const hasCompleteI18n =
            existing &&
            existing.title &&
            existing.title.trim() !== '' &&
            existing.standfirst &&
            existing.standfirst.trim() !== '' &&
            (!sourceI18n.contentMarkdown ||
              (existing.contentMarkdown && existing.contentMarkdown.trim() !== ''))

          if (hasCompleteI18n) {
            results.skipped.push(targetLocale)
            await prisma.translationLog.create({
              data: {
                entityType: TranslationEntityType.HELP_ARTICLE,
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
        }

        // Translate i18n fields
        const needsTitle = !existing || !existing.title || existing.title.trim() === ''
        const needsStandfirst = !existing || !existing.standfirst || existing.standfirst.trim() === ''
        const needsContentMarkdown =
          sourceI18n.contentMarkdown &&
          (!existing || !existing.contentMarkdown || existing.contentMarkdown.trim() === '')
        const needsMetaTitle =
          sourceI18n.metaTitle &&
          (!existing || !existing.metaTitle || existing.metaTitle.trim() === '')
        const needsMetaDesc =
          sourceI18n.metaDescription &&
          (!existing || !existing.metaDescription || existing.metaDescription.trim() === '')

        const titleResult =
          needsTitle || mode === 'force'
            ? await translateText(sourceI18n.title, {
                sourceLocale,
                targetLocale,
                glossary: glossary || undefined,
              })
            : { translated: existing!.title }

        const standfirstResult =
          needsStandfirst || mode === 'force'
            ? await translateText(sourceI18n.standfirst || '', {
                sourceLocale,
                targetLocale,
                glossary: glossary || undefined,
              })
            : { translated: existing!.standfirst || '' }

        const contentMarkdownResult =
          needsContentMarkdown || (mode === 'force' && sourceI18n.contentMarkdown)
            ? await translateMarkdown(sourceI18n.contentMarkdown || '', {
                sourceLocale,
                targetLocale,
                glossary: glossary || undefined,
              })
            : existing?.contentMarkdown
            ? { translated: existing.contentMarkdown }
            : null

        const metaTitleResult =
          needsMetaTitle || (mode === 'force' && sourceI18n.metaTitle)
            ? await translateText(sourceI18n.metaTitle!, {
                sourceLocale,
                targetLocale,
                glossary: glossary || undefined,
              })
            : existing?.metaTitle
            ? { translated: existing.metaTitle }
            : null

        const metaDescResult =
          needsMetaDesc || (mode === 'force' && sourceI18n.metaDescription)
            ? await translateText(sourceI18n.metaDescription!, {
                sourceLocale,
                targetLocale,
                glossary: glossary || undefined,
              })
            : existing?.metaDescription
            ? { translated: existing.metaDescription }
            : null

        // Upsert target i18n
        await prisma.helpArticleI18n.upsert({
          where: {
            articleId_locale: {
              articleId,
              locale: targetLocale,
            },
          },
          create: {
            articleId,
            locale: targetLocale,
            title: titleResult.translated,
            standfirst: standfirstResult.translated || null,
            contentMarkdown: contentMarkdownResult ? contentMarkdownResult.translated : null,
            metaTitle: metaTitleResult ? truncateMeta(metaTitleResult.translated, 60) : null,
            metaDescription: metaDescResult ? truncateMeta(metaDescResult.translated, 160) : null,
            translationStatus: TranslationStatus.MACHINE,
          },
          update:
            mode === 'force'
              ? {
                  title: titleResult.translated,
                  standfirst: standfirstResult.translated || null,
                  contentMarkdown: contentMarkdownResult ? contentMarkdownResult.translated : null,
                  metaTitle: metaTitleResult ? truncateMeta(metaTitleResult.translated, 60) : null,
                  metaDescription: metaDescResult ? truncateMeta(metaDescResult.translated, 160) : null,
                  translationStatus: TranslationStatus.MACHINE,
                }
              : {
                  ...(needsTitle && { title: titleResult.translated }),
                  ...(needsStandfirst && { standfirst: standfirstResult.translated || null }),
                  ...(needsContentMarkdown &&
                    contentMarkdownResult && { contentMarkdown: contentMarkdownResult.translated }),
                  ...(needsMetaTitle &&
                    metaTitleResult && { metaTitle: truncateMeta(metaTitleResult.translated, 60) }),
                  ...(needsMetaDesc &&
                    metaDescResult && { metaDescription: truncateMeta(metaDescResult.translated, 160) }),
                  ...((needsTitle || needsStandfirst || needsContentMarkdown || needsMetaTitle || needsMetaDesc) && {
                    translationStatus: TranslationStatus.MACHINE,
                  }),
                },
        })

        if (existing) {
          results.updated.push(targetLocale)
        } else {
          results.created.push(targetLocale)
        }

        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.HELP_ARTICLE,
            entityId: articleId,
            sourceLocale,
            targetLocale,
            mode,
            status: TranslationLogStatus.SUCCESS,
            model: OPENAI_MODEL,
          },
        })
      } catch (error: any) {
        console.error(`Error translating article to ${targetLocale}:`, error)
        results.errors.push({
          locale: targetLocale,
          error: error.message || 'Translation failed',
        })

        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.HELP_ARTICLE,
            entityId: articleId,
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
    console.error('Error translating article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

