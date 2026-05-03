/**
 * Migration : `HelpArticleI18n.contentMarkdown` → blocs `PARAGRAPH`.
 *
 * Pour chaque `HelpArticleI18n` ayant un `contentMarkdown` non vide ET dont
 * l'article + locale n'a *aucun* `HelpArticleBlock`, crée un unique bloc
 * `PARAGRAPH` (`order = 0`, `data = { text: contentMarkdown }`) qui sera
 * rendu via `<ArticleBlockStream>` côté public (Lot 1.3).
 *
 * Idempotent : si un bloc existe déjà pour (articleId, locale), on **ne
 * touche pas** — quel que soit son type ou son contenu.
 *
 * **DRY-RUN par défaut**. Pour exécuter pour de vrai :
 *   npx tsx scripts/migrate-help-markdown-to-blocks.ts --apply
 *
 * Options :
 *   --apply             Persiste les inserts (sinon : log uniquement).
 *   --collection=<slug> Restreint à une collection (slug).
 *   --locale=<fr|en>    Restreint à une locale.
 *   --truncate-markdown Met à null `contentMarkdown` après insertion (à
 *                       n'utiliser qu'après plusieurs runs sans `--apply`
 *                       et validation visuelle ; conservé séparé pour
 *                       éviter toute perte de données accidentelle).
 *
 * Conforme à la règle de stabilité environnement Arquantix :
 *  - aucune modif de schéma, aucun `down -v`, aucun changement de DB ;
 *  - aucune écriture sans `--apply` ;
 *  - log dense (1 ligne par article migré).
 */

import { PrismaClient, ArticleBlockType } from '@prisma/client'

const prisma = new PrismaClient()

type Args = {
  apply: boolean
  truncateMarkdown: boolean
  collectionSlug: string | null
  locale: string | null
}

function parseArgs(): Args {
  const argv = process.argv.slice(2)
  const args: Args = {
    apply: false,
    truncateMarkdown: false,
    collectionSlug: null,
    locale: null,
  }
  for (const a of argv) {
    if (a === '--apply') args.apply = true
    else if (a === '--truncate-markdown') args.truncateMarkdown = true
    else if (a.startsWith('--collection=')) args.collectionSlug = a.slice('--collection='.length)
    else if (a.startsWith('--locale=')) args.locale = a.slice('--locale='.length)
    else if (a === '--help' || a === '-h') {
      console.log(`Usage : npx tsx scripts/migrate-help-markdown-to-blocks.ts [options]

Options :
  --apply               Persiste les inserts (sinon dry-run).
  --collection=<slug>   Restreint à une collection.
  --locale=<fr|en>      Restreint à une locale.
  --truncate-markdown   Met à null contentMarkdown après insertion.
`)
      process.exit(0)
    } else {
      console.error(`Option inconnue : ${a}`)
      process.exit(2)
    }
  }
  return args
}

async function main() {
  const args = parseArgs()
  console.log('--- Migration help markdown → PARAGRAPH ---')
  console.log(`Mode    : ${args.apply ? 'APPLY (writes!)' : 'DRY-RUN (no writes)'}`)
  if (args.collectionSlug) console.log(`Filter  : collection slug = ${args.collectionSlug}`)
  if (args.locale) console.log(`Filter  : locale = ${args.locale}`)
  if (args.truncateMarkdown) {
    console.log('Truncate: contentMarkdown sera mis à null après insert.')
  }
  console.log('')

  // 1) Récupérer toutes les rows i18n avec contentMarkdown non vide.
  const i18nRows = await prisma.helpArticleI18n.findMany({
    where: {
      contentMarkdown: { not: null },
      ...(args.locale ? { locale: args.locale } : {}),
      ...(args.collectionSlug
        ? {
            article: {
              category: {
                collection: { slug: args.collectionSlug },
              },
            },
          }
        : {}),
    },
    select: {
      id: true,
      articleId: true,
      locale: true,
      contentMarkdown: true,
      article: {
        select: {
          slug: true,
          category: {
            select: {
              slug: true,
              collection: { select: { slug: true } },
            },
          },
        },
      },
    },
  })

  let scanned = 0
  let skippedEmpty = 0
  let skippedExistingBlocks = 0
  let toCreate: Array<{
    i18nRowId: string
    articleId: string
    locale: string
    text: string
    label: string
  }> = []

  for (const row of i18nRows) {
    scanned++
    const text = (row.contentMarkdown ?? '').trim()
    if (text.length === 0) {
      skippedEmpty++
      continue
    }

    const blockCount = await prisma.helpArticleBlock.count({
      where: { articleId: row.articleId, locale: row.locale },
    })
    if (blockCount > 0) {
      skippedExistingBlocks++
      continue
    }

    const label = `[${row.article.category.collection.slug}/${row.article.category.slug}/${row.article.slug}@${row.locale}]`
    toCreate.push({
      i18nRowId: row.id,
      articleId: row.articleId,
      locale: row.locale,
      text,
      label,
    })
  }

  console.log(`Scanned i18n rows         : ${scanned}`)
  console.log(`Skipped (empty markdown)  : ${skippedEmpty}`)
  console.log(`Skipped (existing blocks) : ${skippedExistingBlocks}`)
  console.log(`Will create blocks        : ${toCreate.length}`)
  console.log('')

  if (toCreate.length === 0) {
    console.log('Rien à migrer. Sortie.')
    return
  }

  for (const t of toCreate) {
    const preview = t.text.slice(0, 80).replace(/\s+/g, ' ')
    console.log(
      `${args.apply ? 'CREATE' : 'WOULD CREATE'} PARAGRAPH ${t.label} (${t.text.length} chars) — ${preview}…`
    )
  }

  if (!args.apply) {
    console.log('')
    console.log('DRY-RUN terminé — aucune écriture. Relance avec `--apply` pour persister.')
    return
  }

  console.log('')
  console.log('Application des changements…')
  let created = 0
  let truncated = 0
  for (const t of toCreate) {
    await prisma.$transaction(async (tx) => {
      // Re-vérifier l'absence de blocs au moment de l'insert (concurrence).
      const recheck = await tx.helpArticleBlock.count({
        where: { articleId: t.articleId, locale: t.locale },
      })
      if (recheck > 0) {
        console.log(`SKIP race ${t.label} (blocs créés entre-temps)`)
        return
      }
      await tx.helpArticleBlock.create({
        data: {
          articleId: t.articleId,
          locale: t.locale,
          type: ArticleBlockType.PARAGRAPH,
          data: { text: t.text },
          order: 0,
        },
      })
      created++
      if (args.truncateMarkdown) {
        await tx.helpArticleI18n.update({
          where: { id: t.i18nRowId },
          data: { contentMarkdown: null },
        })
        truncated++
      }
    })
  }

  console.log(`Created blocks            : ${created}`)
  if (args.truncateMarkdown) console.log(`Truncated contentMarkdown : ${truncated}`)
  console.log('Done.')
}

main()
  .catch((err) => {
    console.error('Migration failed:', err)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
