/**
 * Parcourt tous les articles, complète EN / IT :
 * - contenu type Lorem / faux latin → même texte copié (machine) vers en & it ;
 * - sinon → traduction via OpenAI (même logique que l’admin).
 *
 * Prérequis : OPENAI_API_KEY, base Prisma accessible.
 *
 * Usage : npx tsx scripts/translate-all-blog-articles.ts
 */

import { PrismaClient } from '@prisma/client'
import { getGlossary } from '@/lib/translate/getGlossary'
import { isLoremIpsumOrLatinPlaceholder } from '@/lib/translate/isLoremIpsumOrLatinPlaceholder'
import { copyArticleLocalesFromSource } from '@/lib/translate/copyArticleLocalesFromSource'
import { translateArticleToTargetLocale } from '@/lib/translate/translateArticleToTargetLocale'

const prisma = new PrismaClient()

const PREFERRED_SOURCE_ORDER = ['fr', 'en', 'it'] as const
const TARGET_LOCALES = ['en', 'it'] as const

async function resolveSourceLocale(articleId: string): Promise<string | null> {
  for (const loc of PREFERRED_SOURCE_ORDER) {
    const row = await prisma.articleI18n.findUnique({
      where: { articleId_locale: { articleId, locale: loc } },
    })
    if (row && row.title.trim() !== '') return loc
  }
  return null
}

/** Texte agrégé pour détection Lorem (titre, chapô, méta, JSON des blocs). */
async function buildCombinedDetectionText(articleId: string, sourceLocale: string): Promise<string> {
  const i18n = await prisma.articleI18n.findUnique({
    where: { articleId_locale: { articleId, locale: sourceLocale } },
  })
  const blocks = await prisma.articleBlock.findMany({
    where: { articleId },
    orderBy: { order: 'asc' },
  })
  const blockRows = await prisma.articleBlockI18n.findMany({
    where: { block: { articleId }, locale: sourceLocale },
  })
  const byBlock = new Map(blockRows.map((r) => [r.blockId, r.data]))

  const parts: string[] = []
  if (i18n) {
    parts.push(i18n.title, i18n.standfirst)
    if (i18n.metaTitle) parts.push(i18n.metaTitle)
    if (i18n.metaDescription) parts.push(i18n.metaDescription)
    if (i18n.coverTitle) parts.push(i18n.coverTitle)
  }
  for (const b of blocks) {
    const raw = byBlock.get(b.id) ?? b.data
    parts.push(typeof raw === 'string' ? raw : JSON.stringify(raw))
  }
  return parts.filter((p) => p && p.trim()).join('\n\n')
}

async function main() {
  const glossary = await getGlossary()
  const articles = await prisma.article.findMany({
    select: { id: true, slug: true },
    orderBy: { updatedAt: 'desc' },
  })

  console.log(`${articles.length} article(s) à traiter.\n`)

  for (const a of articles) {
    const sourceLocale = await resolveSourceLocale(a.id)
    if (!sourceLocale) {
      console.log(`— [${a.slug}] ignoré : aucun i18n FR/EN/IT avec titre.`)
      continue
    }

    const targets = TARGET_LOCALES.filter((l) => l !== sourceLocale)
    if (targets.length === 0) {
      console.log(`— [${a.slug}] rien à faire (source déjà en en/it).`)
      continue
    }

    const combined = await buildCombinedDetectionText(a.id, sourceLocale)
    const lorem = isLoremIpsumOrLatinPlaceholder(combined)

    if (lorem) {
      await copyArticleLocalesFromSource(prisma, a.id, sourceLocale, [...targets])
      console.log(`✓ [${a.slug}] copie Lorem / faux latin → ${targets.join(', ')} (même contenu)`)
      continue
    }

    const sourceI18n = await prisma.articleI18n.findUnique({
      where: { articleId_locale: { articleId: a.id, locale: sourceLocale } },
    })
    if (!sourceI18n) continue

    const sourceBlocks = await prisma.articleBlock.findMany({
      where: { articleId: a.id },
      orderBy: { order: 'asc' },
    })

    for (const targetLocale of targets) {
      try {
        const r = await translateArticleToTargetLocale({
          prisma,
          articleId: a.id,
          sourceLocale,
          targetLocale,
          mode: 'missing',
          sourceI18n,
          sourceBlocks,
          glossary,
        })
        if (r.kind === 'skipped') {
          console.log(`  · [${a.slug}] ${targetLocale} : déjà complet — ignoré`)
        } else {
          console.log(
            `  · [${a.slug}] ${targetLocale} : ${r.wasUpdate ? 'mis à jour' : 'créé'} (traduction)`,
          )
        }
      } catch (e) {
        console.error(`  ✗ [${a.slug}] ${targetLocale} :`, e)
      }
    }
  }

  console.log('\nTerminé.')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
