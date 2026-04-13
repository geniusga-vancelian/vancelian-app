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
import { ArticleBlockType } from '@prisma/client'

const translateArticleSchema = z.object({
  articleId: z.string().min(1),
  sourceLocale: z.string().refine(isValidLocale, { message: 'Invalid source locale' }),
  targetLocales: z.array(z.string().refine(isValidLocale, { message: 'Invalid target locale' })).min(1).max(10),
  mode: z.enum(['missing', 'force']).default('missing'),
})

// Truncate meta fields to SEO limits
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

    // Get source article i18n
    const sourceI18n = await prisma.articleI18n.findUnique({
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

    // Get source blocks
    const sourceBlocks = await prisma.articleBlock.findMany({
      where: { articleId },
      orderBy: { order: 'asc' },
    })

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
        // Check if target already exists
        const existing = await prisma.articleI18n.findUnique({
          where: {
            articleId_locale: {
              articleId,
              locale: targetLocale,
            },
          },
        })

        // Check existing block translations
        const existingBlockI18n = await prisma.articleBlockI18n.findMany({
          where: {
            block: { articleId },
            locale: targetLocale,
          },
        })
        const existingBlockIds = new Set(existingBlockI18n.map((bi) => bi.blockId))

        // In "missing" mode, check if translation is actually needed
        if (mode === 'missing') {
          // Check if ArticleI18n exists and has all required fields
          const hasCompleteI18n =
            existing &&
            existing.title &&
            existing.title.trim() !== '' &&
            existing.standfirst &&
            existing.standfirst.trim() !== ''

          // Check if all blocks have translations
          const allBlocksTranslated = sourceBlocks.every((block) => existingBlockIds.has(block.id))

          // If both i18n and blocks are complete, skip
          if (hasCompleteI18n && allBlocksTranslated) {
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
          // Otherwise, proceed with translation (will update missing fields/blocks)
        }

        // Log translation start (dev only)
        if (process.env.NODE_ENV !== 'production') {
          console.log(
            `[Translate][ARTICLE][${articleId}] source=${sourceLocale} target=${targetLocale} mode=${mode}`
          )
        }

        // Translate i18n fields
        // In "missing" mode, only translate fields that are missing or empty
        const needsTitle = !existing || !existing.title || existing.title.trim() === ''
        const needsStandfirst = !existing || !existing.standfirst || existing.standfirst.trim() === ''
        const needsCoverTitle =
          sourceI18n.coverTitle &&
          (!existing || !existing.coverTitle || existing.coverTitle.trim() === '')
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
            ? await translateText(sourceI18n.standfirst, {
                sourceLocale,
                targetLocale,
                glossary: glossary || undefined,
              })
            : { translated: existing!.standfirst }

        const coverTitleResult =
          needsCoverTitle || (mode === 'force' && sourceI18n.coverTitle)
            ? await translateText(sourceI18n.coverTitle!, {
                sourceLocale,
                targetLocale,
                glossary: glossary || undefined,
              })
            : existing?.coverTitle
            ? { translated: existing.coverTitle }
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

        // Upsert target i18n with MACHINE status
        // CRITICAL: Ensure locale is correctly set in where clause to prevent mixing
        // In "missing" mode, only update fields that were translated
        const upsertResult = await prisma.articleI18n.upsert({
          where: {
            articleId_locale: {
              articleId,
              locale: targetLocale, // ✅ Explicitly set target locale
            },
          },
          create: {
            articleId,
            locale: targetLocale, // ✅ Explicitly set target locale
            title: titleResult.translated,
            standfirst: standfirstResult.translated,
            coverTitle: coverTitleResult ? coverTitleResult.translated : null,
            metaTitle: metaTitleResult ? truncateMeta(metaTitleResult.translated, 60) : null,
            metaDescription: metaDescResult ? truncateMeta(metaDescResult.translated, 160) : null,
            translationStatus: TranslationStatus.MACHINE,
          },
          update:
            mode === 'force'
              ? {
                  title: titleResult.translated,
                  standfirst: standfirstResult.translated,
                  coverTitle: coverTitleResult ? coverTitleResult.translated : null,
                  metaTitle: metaTitleResult ? truncateMeta(metaTitleResult.translated, 60) : null,
                  metaDescription: metaDescResult ? truncateMeta(metaDescResult.translated, 160) : null,
                  translationStatus: TranslationStatus.MACHINE,
                }
              : {
                  // Only update fields that were translated (in missing mode)
                  ...(needsTitle && { title: titleResult.translated }),
                  ...(needsStandfirst && { standfirst: standfirstResult.translated }),
                  ...(needsCoverTitle && coverTitleResult && { coverTitle: coverTitleResult.translated }),
                  ...(needsMetaTitle &&
                    metaTitleResult && { metaTitle: truncateMeta(metaTitleResult.translated, 60) }),
                  ...(needsMetaDesc &&
                    metaDescResult && { metaDescription: truncateMeta(metaDescResult.translated, 160) }),
                  // Always update translation status if any field was translated
                  ...((needsTitle || needsStandfirst || needsCoverTitle || needsMetaTitle || needsMetaDesc) && {
                    translationStatus: TranslationStatus.MACHINE,
                  }),
                },
        })

        // Verify the write (dev only)
        if (process.env.NODE_ENV !== 'production') {
          const verify = await prisma.articleI18n.findUnique({
            where: {
              articleId_locale: {
                articleId,
                locale: targetLocale,
              },
            },
          })
          if (verify && verify.locale !== targetLocale) {
            console.error(
              `[Translate][ARTICLE] ERROR: Written locale mismatch! Expected ${targetLocale}, got ${verify.locale}`
            )
          }
        }

        // Translate blocks per locale (stored in ArticleBlockI18n)
        let blocksTranslatedCount = 0
        for (const sourceBlock of sourceBlocks) {
          try {
            // In "missing" mode, skip blocks that already have translations
            if (mode === 'missing' && existingBlockIds.has(sourceBlock.id)) {
              continue
            }

            // Deep clone block data to avoid mutating original
            const blockData = typeof structuredClone !== 'undefined'
              ? structuredClone(sourceBlock.data)
              : JSON.parse(JSON.stringify(sourceBlock.data))

            let translatedBlockData = blockData

            // Translate based on block type
            if (sourceBlock.type === ArticleBlockType.HEADING) {
              const headingText = (blockData as any).text || ''
              if (headingText && typeof headingText === 'string' && headingText.trim()) {
                const result = await translateText(headingText, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                translatedBlockData = { ...blockData, text: result.translated }
              }
            } else if (sourceBlock.type === ArticleBlockType.PARAGRAPH) {
              const paragraphText = (blockData as any).text || ''
              if (paragraphText && typeof paragraphText === 'string' && paragraphText.trim()) {
                const result = await translateMarkdown(paragraphText, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                translatedBlockData = { ...blockData, text: result.translated }
              }
            } else if (sourceBlock.type === ArticleBlockType.QUOTE) {
              const quoteText = (blockData as any).text || ''
              const quoteAuthor = (blockData as any).author || ''
              if (quoteText && typeof quoteText === 'string' && quoteText.trim()) {
                const textResult = await translateText(quoteText, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                const authorResult =
                  quoteAuthor && typeof quoteAuthor === 'string' && quoteAuthor.trim()
                    ? await translateText(quoteAuthor, {
                        sourceLocale,
                        targetLocale,
                        glossary: glossary || undefined,
                      })
                    : null
                translatedBlockData = {
                  ...blockData,
                  text: textResult.translated,
                  author: authorResult ? authorResult.translated : quoteAuthor,
                }
              }
            } else if (sourceBlock.type === ArticleBlockType.BULLET_LIST) {
              const items = (blockData as any).items || []
              if (Array.isArray(items) && items.length > 0) {
                const translatedItems = await Promise.all(
                  items.map(async (item: any) => {
                    if (typeof item === 'string' && item.trim()) {
                      const result = await translateText(item, {
                        sourceLocale,
                        targetLocale,
                        glossary: glossary || undefined,
                      })
                      return result.translated
                    }
                    return item
                  })
                )
                translatedBlockData = { ...blockData, items: translatedItems }
              }
            } else if (sourceBlock.type === ArticleBlockType.IMAGE) {
              // Translate caption if present, keep mediaId unchanged
              const caption = (blockData as any).caption || ''
              if (caption && typeof caption === 'string' && caption.trim()) {
                const result = await translateText(caption, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                translatedBlockData = { ...blockData, caption: result.translated }
              }
            } else if (sourceBlock.type === ArticleBlockType.VIDEO) {
              // Translate caption/title if present, keep url unchanged
              const caption = (blockData as any).caption || ''
              const title = (blockData as any).title || ''
              if (caption && typeof caption === 'string' && caption.trim()) {
                const result = await translateText(caption, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                translatedBlockData = { ...blockData, caption: result.translated }
              }
              if (title && typeof title === 'string' && title.trim()) {
                const titleResult = await translateText(title, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                translatedBlockData = { ...translatedBlockData, title: titleResult.translated }
              }
            } else if (sourceBlock.type === ArticleBlockType.DOCUMENT) {
              // Translate title if present, keep mediaId unchanged
              const title = (blockData as any).title || ''
              if (title && typeof title === 'string' && title.trim()) {
                const result = await translateText(title, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                translatedBlockData = { ...blockData, title: result.translated }
              }
            }
            // For blocks with no translatable content, keep data as-is

            // Upsert translated block i18n
            await prisma.articleBlockI18n.upsert({
              where: {
                blockId_locale: {
                  blockId: sourceBlock.id,
                  locale: targetLocale,
                },
              },
              create: {
                blockId: sourceBlock.id,
                locale: targetLocale,
                data: translatedBlockData,
                translationStatus: TranslationStatus.MACHINE,
              },
              update: {
                data: translatedBlockData,
                translationStatus: TranslationStatus.MACHINE,
              },
            })

            blocksTranslatedCount++
          } catch (blockError: any) {
            console.error(`Error translating block ${sourceBlock.id} to ${targetLocale}:`, blockError)
            // Continue with other blocks even if one fails
          }
        }

        // Log blocks translation (dev only)
        if (process.env.NODE_ENV !== 'production') {
          console.log(
            `[Translate][ARTICLE][${articleId}] Translated ${blocksTranslatedCount}/${sourceBlocks.length} blocks to ${targetLocale}`
          )
        }

        // Log success
        await prisma.translationLog.create({
          data: {
            entityType: TranslationEntityType.ARTICLE,
            entityId: articleId,
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
        console.error(`Error translating article to ${targetLocale}:`, error)
        const errorMessage = error.message || 'Translation failed'
        results.errors.push({
          locale: targetLocale,
          error: errorMessage,
        })

        // Log error
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
        { status: 400 }
      )
    }
    console.error('Error in translate article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

