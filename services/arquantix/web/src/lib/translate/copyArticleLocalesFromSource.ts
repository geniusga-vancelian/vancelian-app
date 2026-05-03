import type { PrismaClient } from '@prisma/client'
import { Prisma, TranslationStatus } from '@prisma/client'

/**
 * Duplique le contenu éditorial de `sourceLocale` vers `targetLocales` (mêmes chaînes + mêmes JSON de blocs).
 * Utilisé pour Lorem / faux texte : EN et IT reçoivent la même teneur que la source.
 */
export async function copyArticleLocalesFromSource(
  prisma: PrismaClient,
  articleId: string,
  sourceLocale: string,
  targetLocales: string[],
): Promise<void> {
  const sourceI18n = await prisma.articleI18n.findUnique({
    where: { articleId_locale: { articleId, locale: sourceLocale } },
  })
  if (!sourceI18n) {
    throw new Error(`Article i18n manquant: ${articleId} / ${sourceLocale}`)
  }

  const blocks = await prisma.articleBlock.findMany({
    where: { articleId },
    orderBy: { order: 'asc' },
  })

  const blockI18nRows = await prisma.articleBlockI18n.findMany({
    where: { block: { articleId }, locale: sourceLocale },
  })
  const byBlock = new Map(blockI18nRows.map((r) => [r.blockId, r.data]))

  for (const targetLocale of targetLocales) {
    if (targetLocale === sourceLocale) continue

    await prisma.articleI18n.upsert({
      where: { articleId_locale: { articleId, locale: targetLocale } },
      create: {
        articleId,
        locale: targetLocale,
        title: sourceI18n.title,
        standfirst: sourceI18n.standfirst,
        coverTitle: sourceI18n.coverTitle,
        metaTitle: sourceI18n.metaTitle,
        metaDescription: sourceI18n.metaDescription,
        translationStatus: TranslationStatus.MACHINE,
      },
      update: {
        title: sourceI18n.title,
        standfirst: sourceI18n.standfirst,
        coverTitle: sourceI18n.coverTitle,
        metaTitle: sourceI18n.metaTitle,
        metaDescription: sourceI18n.metaDescription,
        translationStatus: TranslationStatus.MACHINE,
      },
    })

    for (const block of blocks) {
      const effective = byBlock.get(block.id) ?? block.data
      const data = JSON.parse(JSON.stringify(effective)) as Prisma.InputJsonValue
      await prisma.articleBlockI18n.upsert({
        where: { blockId_locale: { blockId: block.id, locale: targetLocale } },
        create: {
          blockId: block.id,
          locale: targetLocale,
          data,
          translationStatus: TranslationStatus.MACHINE,
        },
        update: {
          data,
          translationStatus: TranslationStatus.MACHINE,
        },
      })
    }
  }
}
