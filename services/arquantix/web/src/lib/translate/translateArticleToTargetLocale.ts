import type { PrismaClient } from '@prisma/client'
import {
  ArticleBlockType,
  TranslationEntityType,
  TranslationLogStatus,
  TranslationStatus,
} from '@prisma/client'
import type { ArticleBlock, ArticleI18n } from '@prisma/client'
import { translateText } from '@/lib/translate/translateText'
import { translateMarkdown } from '@/lib/translate/translateMarkdown'
import { OPENAI_MODEL } from '@/lib/openai/client'
import { getGlossary } from '@/lib/translate/getGlossary'

function truncateMeta(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
}

export type TranslateArticleToTargetResult =
  | { kind: 'skipped' }
  | { kind: 'success'; wasUpdate: boolean }

type GlossaryT = Awaited<ReturnType<typeof getGlossary>>

/**
 * Cœur de `POST /api/admin/translate/article` pour **une** locale cible.
 * Utilise `article_block_i18n` pour la locale source quand présent, sinon `article_blocks.data`.
 */
export async function translateArticleToTargetLocale(params: {
  prisma: PrismaClient
  articleId: string
  sourceLocale: string
  targetLocale: string
  mode: 'missing' | 'force'
  sourceI18n: ArticleI18n
  sourceBlocks: ArticleBlock[]
  glossary: GlossaryT
}): Promise<TranslateArticleToTargetResult> {
  const { prisma, articleId, sourceLocale, targetLocale, mode, sourceI18n, sourceBlocks, glossary } =
    params

  if (targetLocale === sourceLocale) {
    return { kind: 'skipped' }
  }

  const sourceBlockI18nRows = await prisma.articleBlockI18n.findMany({
    where: { block: { articleId }, locale: sourceLocale },
  })
  const sourceBlockDataById = new Map(sourceBlockI18nRows.map((r) => [r.blockId, r.data]))

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
            return { kind: 'skipped' }
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
        await prisma.articleI18n.upsert({
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

            // Source éditorial : i18n de la langue source, sinon données canoniques du bloc
            const blockDataRaw = sourceBlockDataById.get(sourceBlock.id) ?? sourceBlock.data
            const blockData = typeof structuredClone !== 'undefined'
              ? structuredClone(blockDataRaw as object)
              : JSON.parse(JSON.stringify(blockDataRaw))

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
            } else if (
              sourceBlock.type === ArticleBlockType.MEDIA_IMAGE_CAROUSEL ||
              sourceBlock.type === ArticleBlockType.LOCALISATION
            ) {
              const moduleTitle = (blockData as any).moduleTitle || ''
              const description = (blockData as any).description || ''
              let next: any = { ...blockData }
              if (moduleTitle && typeof moduleTitle === 'string' && moduleTitle.trim()) {
                const r = await translateText(moduleTitle, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                next = { ...next, moduleTitle: r.translated }
              }
              if (description && typeof description === 'string' && description.trim()) {
                const r = await translateText(description, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                next = { ...next, description: r.translated }
              }
              translatedBlockData = next
            } else if (sourceBlock.type === ArticleBlockType.DOCUMENTS_LIST) {
              const subtitle = (blockData as any).subtitle || ''
              const moduleTitle = (blockData as any).moduleTitle || ''
              const description = (blockData as any).description || ''
              let next: any = { ...blockData }
              if (subtitle && typeof subtitle === 'string' && subtitle.trim()) {
                const r = await translateText(subtitle, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                next = { ...next, subtitle: r.translated }
              }
              if (moduleTitle && typeof moduleTitle === 'string' && moduleTitle.trim()) {
                const r = await translateText(moduleTitle, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                next = { ...next, moduleTitle: r.translated }
              }
              if (description && typeof description === 'string' && description.trim()) {
                const r = await translateText(description, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                next = { ...next, description: r.translated }
              }
              const entries = Array.isArray((blockData as any).documentEntries)
                ? (blockData as any).documentEntries
                : []
              if (Array.isArray(entries) && entries.length > 0) {
                const nextEntries = await Promise.all(
                  entries.map(async (ent: any) => {
                    if (ent == null || typeof ent !== 'object') return ent
                    const name = typeof ent.documentName === 'string' ? ent.documentName : ''
                    if (name.trim()) {
                      const r = await translateText(name, {
                        sourceLocale,
                        targetLocale,
                        glossary: glossary || undefined,
                      })
                      return { ...ent, documentName: r.translated }
                    }
                    return ent
                  })
                )
                next = { ...next, documentEntries: nextEntries }
              }
              translatedBlockData = next
            } else if (sourceBlock.type === ArticleBlockType.KEY_INFORMATION) {
              const bd = blockData as Record<string, unknown>
              const moduleTitle = typeof bd.title === 'string' ? bd.title : ''
              const ctaL = typeof bd.ctaLabel === 'string' ? bd.ctaLabel : ''
              let next: Record<string, unknown> = { ...bd }
              if (moduleTitle && moduleTitle.trim()) {
                const r = await translateText(moduleTitle, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                next = { ...next, title: r.translated }
              }
              if (ctaL && ctaL.trim()) {
                const r = await translateText(ctaL, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                next = { ...next, ctaLabel: r.translated }
              }
              const rows = Array.isArray(bd.rows) ? bd.rows : []
              if (Array.isArray(rows) && rows.length > 0) {
                const nextRows = await Promise.all(
                  rows.map(async (ent: unknown) => {
                    if (ent == null || typeof ent !== 'object' || Array.isArray(ent)) return ent
                    const o = ent as Record<string, unknown>
                    const la = typeof o.label === 'string' ? o.label : ''
                    const va = typeof o.value === 'string' ? o.value : ''
                    let row: Record<string, unknown> = { ...o }
                    if (la.trim()) {
                      const r1 = await translateText(la, {
                        sourceLocale,
                        targetLocale,
                        glossary: glossary || undefined,
                      })
                      row = { ...row, label: r1.translated }
                    }
                    if (va.trim()) {
                      const r2 = await translateText(va, {
                        sourceLocale,
                        targetLocale,
                        glossary: glossary || undefined,
                      })
                      row = { ...row, value: r2.translated }
                    }
                    return row
                  }),
                )
                next = { ...next, rows: nextRows }
              }
              translatedBlockData = next
            } else if (sourceBlock.type === ArticleBlockType.VIDEO_BLOCK_ARTICLE) {
              const bd = blockData as Record<string, unknown>
              const modTitle = typeof bd.title === 'string' ? bd.title : ''
              let next: Record<string, unknown> = { ...bd }
              if (modTitle && modTitle.trim()) {
                const r = await translateText(modTitle, {
                  sourceLocale,
                  targetLocale,
                  glossary: glossary || undefined,
                })
                next = { ...next, title: r.translated }
              }
              const items = Array.isArray(bd.items) ? bd.items : []
              if (Array.isArray(items) && items.length > 0) {
                const nextItems = await Promise.all(
                  items.map(async (it: unknown) => {
                    if (it == null || typeof it !== 'object' || Array.isArray(it)) return it
                    const o = it as Record<string, unknown>
                    const t = typeof o.title === 'string' ? o.title : ''
                    const dateStr = typeof o.date === 'string' ? o.date : ''
                    let row: Record<string, unknown> = { ...o }
                    if (t.trim()) {
                      const r1 = await translateText(t, {
                        sourceLocale,
                        targetLocale,
                        glossary: glossary || undefined,
                      })
                      row = { ...row, title: r1.translated }
                    }
                    if (dateStr.trim()) {
                      const r2 = await translateText(dateStr, {
                        sourceLocale,
                        targetLocale,
                        glossary: glossary || undefined,
                      })
                      row = { ...row, date: r2.translated }
                    }
                    return row
                  }),
                )
                next = { ...next, items: nextItems }
              }
              translatedBlockData = next
            } else if (sourceBlock.type === ArticleBlockType.HOW_IT_WORKS_CAROUSEL) {
              // Calque section CMS `how_it_works` : on traduit les libellés
              // visibles (label / title / subtitle, CTAs globaux, et pour
              // chaque step : number, title, description, stepButtonLabel).
              // On NE traduit PAS : `imageMediaId`, `imageMediaUrl`,
              // `imageMediaAlt`, `stepButtonHref`, `primaryCtaHref`,
              // `secondaryCtaHref`, `hideStepNumbering`, `surface`.
              const bd = blockData as Record<string, unknown>
              let next: Record<string, unknown> = { ...bd }
              for (const key of [
                'label',
                'title',
                'subtitle',
                'primaryCtaText',
                'secondaryCtaText',
              ] as const) {
                const s = typeof bd[key] === 'string' ? (bd[key] as string) : ''
                if (s.trim()) {
                  const r = await translateText(s, {
                    sourceLocale,
                    targetLocale,
                    glossary: glossary || undefined,
                  })
                  next = { ...next, [key]: r.translated }
                }
              }
              const steps = Array.isArray(bd.steps) ? bd.steps : []
              if (steps.length > 0) {
                const nextSteps = await Promise.all(
                  steps.map(async (it) => {
                    if (it == null || typeof it !== 'object' || Array.isArray(it)) return it
                    const o = it as Record<string, unknown>
                    let row: Record<string, unknown> = { ...o }
                    for (const key of [
                      'number',
                      'title',
                      'description',
                      'stepButtonLabel',
                    ] as const) {
                      const s = typeof o[key] === 'string' ? (o[key] as string) : ''
                      if (s.trim()) {
                        const r = await translateText(s, {
                          sourceLocale,
                          targetLocale,
                          glossary: glossary || undefined,
                        })
                        row = { ...row, [key]: r.translated }
                      }
                    }
                    return row
                  }),
                )
                next = { ...next, steps: nextSteps }
              }
              translatedBlockData = next
            } else if (sourceBlock.type === ArticleBlockType.STEPS_MODULE) {
              const bd = blockData as Record<string, unknown>
              let next: Record<string, unknown> = { ...bd }
              for (const key of ['title', 'subtitle', 'description', 'rightLabel'] as const) {
                const s = typeof bd[key] === 'string' ? (bd[key] as string) : ''
                if (s.trim()) {
                  const r = await translateText(s, {
                    sourceLocale,
                    targetLocale,
                    glossary: glossary || undefined,
                  })
                  next = { ...next, [key]: r.translated }
                }
              }
              const items = Array.isArray(bd.items) ? bd.items : []
              if (items.length > 0) {
                const nextItems = await Promise.all(
                  items.map(async (it) => {
                    if (it == null || typeof it !== 'object' || Array.isArray(it)) return it
                    const o = it as Record<string, unknown>
                    let row: Record<string, unknown> = { ...o }
                    const title = typeof o.title === 'string' ? o.title : ''
                    const dateStr = typeof o.date === 'string' ? o.date : ''
                    const dayLabel = typeof o.dayLabel === 'string' ? o.dayLabel : ''
                    const desc = typeof o.description === 'string' ? o.description : ''
                    if (title.trim()) {
                      const r1 = await translateText(title, {
                        sourceLocale,
                        targetLocale,
                        glossary: glossary || undefined,
                      })
                      row = { ...row, title: r1.translated }
                    }
                    if (dateStr.trim()) {
                      const r2 = await translateText(dateStr, {
                        sourceLocale,
                        targetLocale,
                        glossary: glossary || undefined,
                      })
                      row = { ...row, date: r2.translated }
                    }
                    if (dayLabel.trim()) {
                      const r3 = await translateText(dayLabel, {
                        sourceLocale,
                        targetLocale,
                        glossary: glossary || undefined,
                      })
                      row = { ...row, dayLabel: r3.translated }
                    }
                    if (desc.trim()) {
                      const r4 = await translateText(desc, {
                        sourceLocale,
                        targetLocale,
                        glossary: glossary || undefined,
                      })
                      row = { ...row, description: r4.translated }
                    }
                    const tagsRaw = o.tags
                    if (tagsRaw instanceof Array && tagsRaw.length > 0) {
                      const nextTags = await Promise.all(
                        tagsRaw.map(async (t) => {
                          if (typeof t !== 'string' || !t.trim()) return t
                          const rt = await translateText(t, {
                            sourceLocale,
                            targetLocale,
                            glossary: glossary || undefined,
                          })
                          return rt.translated
                        }),
                      )
                      row = { ...row, tags: nextTags }
                    }
                    return row
                  }),
                )
                next = { ...next, items: nextItems }
              }
              translatedBlockData = next
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

        return { kind: 'success', wasUpdate: Boolean(existing) }
}
