/**
 * Migration : `HelpArticle` (+ `HelpArticleI18n`, `HelpArticleBlock`) →
 * `Article` (`articleType='HELP'`) + `ArticleI18n` + `ArticleBlock` /
 * `ArticleBlockI18n`.
 *
 * Stratégie (validée Phase 3) :
 *   - cut-over net (un seul cycle dry-run / apply, pas de double-write) ;
 *   - i18n cible = table séparée comme le blog (`ArticleI18n` + `ArticleBlockI18n`) ;
 *   - cible = arquantix LOCAL d'abord, prod plus tard ;
 *   - HELP est conservé dans une hiérarchie `Collection > Category > Article` :
 *     `Article.helpCollectionId`, `Article.helpCategoryId`, `Article.helpSlug`
 *     (colonnes nullables ajoutées Phase 3.1, contraintes uniques sur
 *     `(helpCategoryId, helpSlug)`).
 *
 * Particularités sources vs cibles :
 *   - `HelpArticleBlock` est *par locale* (5 blocs en EN ≠ 4 en FR possible).
 *     `ArticleBlock` est *partagé* + `ArticleBlockI18n` *par locale*. On
 *     choisit donc une « primary locale » comme structure de référence
 *     (ordre + types des blocs), puis on duplique les `data` localisées
 *     dans `ArticleBlockI18n` en matchant par `order`. Toute anomalie
 *     (counts différents, types qui ne matchent pas pour un même order)
 *     est loggée comme WARNING mais ne bloque pas la migration.
 *   - `HelpArticleI18n.contentMarkdown` n'a *pas* d'équivalent sur
 *     `ArticleI18n`. Ce script ne le migre pas. Si `contentMarkdown` est
 *     non vide ET qu'il n'y a aucun `HelpArticleBlock` pour cette locale,
 *     on logge un WARNING (l'admin doit lancer
 *     `migrate-help-markdown-to-blocks.ts --apply` AVANT ce script).
 *   - `Article.slug` est `@unique` global. On le calcule à partir de
 *     `help-{collectionSlug}-{categorySlug}-{helpSlug}` avec dédup
 *     `-2`, `-3`, … en cas de collision (rare mais possible).
 *   - `Article.authorName` est NOT NULL. Fallback à "Vancelian" si
 *     `HelpArticle.authorName` est null.
 *   - `ArticleI18n.standfirst` est NOT NULL. Fallback à "" si null.
 *
 * Idempotence :
 *   Si un `Article` existe déjà avec `helpCategoryId == X` ET
 *   `helpSlug == Y`, on SKIP (l'admin doit supprimer / re-créer
 *   manuellement s'il veut re-migrer un article).
 *
 * **DRY-RUN par défaut**. Pour exécuter pour de vrai :
 *   npx tsx scripts/migrate-help-to-article.ts --apply
 *
 * Options :
 *   --apply                   Persiste les inserts (sinon : log uniquement).
 *   --collection=<slug>       Restreint à une collection (slug).
 *   --category=<slug>         Restreint à une catégorie (slug ; combinable avec --collection).
 *   --locale=<csv>            Restreint aux locales données (ex: fr,en). Défaut : toutes.
 *   --primary-locale=<loc>    Locale de référence pour la structure des blocs. Défaut :
 *                             priorité descendante en, fr, puis première locale trouvée.
 *   --limit=<N>               Limite le nombre d'articles traités.
 *   --verbose                 Log dense (par bloc).
 *
 * Conforme à la règle de stabilité environnement Arquantix :
 *  - aucune modif de schéma, aucun `down -v`, aucun changement de DB ;
 *  - aucune écriture sans `--apply` ;
 *  - log dense (1 ligne par article) ;
 *  - chaque article migré = 1 transaction (rollback en cas d'erreur).
 */

import { PrismaClient, Prisma, ArticleBlockType, ContentStatus, TranslationStatus } from '@prisma/client'

const prisma = new PrismaClient()

type Args = {
  apply: boolean
  collectionSlug: string | null
  categorySlug: string | null
  locales: string[] | null
  primaryLocale: string | null
  limit: number | null
  verbose: boolean
}

const DEFAULT_PRIMARY_LOCALES = ['en', 'fr']

function parseArgs(): Args {
  const argv = process.argv.slice(2)
  const args: Args = {
    apply: false,
    collectionSlug: null,
    categorySlug: null,
    locales: null,
    primaryLocale: null,
    limit: null,
    verbose: false,
  }
  for (const a of argv) {
    if (a === '--apply') args.apply = true
    else if (a === '--verbose') args.verbose = true
    else if (a.startsWith('--collection=')) args.collectionSlug = a.slice('--collection='.length)
    else if (a.startsWith('--category=')) args.categorySlug = a.slice('--category='.length)
    else if (a.startsWith('--locale=')) {
      args.locales = a
        .slice('--locale='.length)
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
    } else if (a.startsWith('--primary-locale=')) args.primaryLocale = a.slice('--primary-locale='.length)
    else if (a.startsWith('--limit=')) {
      const n = Number.parseInt(a.slice('--limit='.length), 10)
      if (Number.isFinite(n) && n > 0) args.limit = n
    } else if (a === '--help' || a === '-h') {
      console.log(`Usage : npx tsx scripts/migrate-help-to-article.ts [options]

Options :
  --apply                  Persiste les inserts (sinon : dry-run, lecture seule).
  --collection=<slug>      Restreint à une collection (slug).
  --category=<slug>        Restreint à une catégorie (combinable avec --collection).
  --locale=<csv>           Restreint aux locales (ex: fr,en).
  --primary-locale=<loc>   Locale de référence pour la structure des blocs.
                           Défaut : 'en' > 'fr' > première trouvée.
  --limit=<N>              Limite le nombre d'articles traités.
  --verbose                Log par bloc.
`)
      process.exit(0)
    }
  }
  return args
}

type LoadedHelpArticle = Prisma.HelpArticleGetPayload<{
  include: {
    category: { include: { collection: true } }
    i18n: true
    blocks: true
  }
}>

function pickPrimaryLocale(
  available: string[],
  override: string | null,
): string | null {
  if (available.length === 0) return null
  if (override && available.includes(override)) return override
  for (const loc of DEFAULT_PRIMARY_LOCALES) {
    if (available.includes(loc)) return loc
  }
  return available[0]
}

async function ensureUniqueSlug(baseSlug: string, taken: Set<string>): Promise<string> {
  const sanitized = baseSlug
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
  if (!sanitized) return `help-${Date.now()}`
  if (!taken.has(sanitized)) {
    const exists = await prisma.article.findUnique({ where: { slug: sanitized }, select: { id: true } })
    if (!exists) {
      taken.add(sanitized)
      return sanitized
    }
    taken.add(sanitized)
  }
  let i = 2
  while (true) {
    const candidate = `${sanitized}-${i}`
    if (!taken.has(candidate)) {
      const exists = await prisma.article.findUnique({ where: { slug: candidate }, select: { id: true } })
      if (!exists) {
        taken.add(candidate)
        return candidate
      }
      taken.add(candidate)
    }
    i++
    if (i > 1000) throw new Error(`Impossible de générer un slug unique pour "${baseSlug}" après 1000 tentatives`)
  }
}

type Stats = {
  total: number
  alreadyMigrated: number
  migrated: number
  errors: number
  warnings: number
  blocksCreated: number
  blockI18nCreated: number
}

async function migrateOne(
  helpArticle: LoadedHelpArticle,
  args: Args,
  takenSlugs: Set<string>,
  stats: Stats,
): Promise<void> {
  const { category, i18n, blocks } = helpArticle
  const collection = category.collection

  const requestedLocales = args.locales
  const i18nFiltered = requestedLocales ? i18n.filter((row) => requestedLocales.includes(row.locale)) : i18n
  const blocksFiltered = requestedLocales ? blocks.filter((b) => requestedLocales.includes(b.locale)) : blocks

  if (i18nFiltered.length === 0) {
    console.warn(
      `  [SKIP] HelpArticle ${helpArticle.id} ("${helpArticle.slug}") n'a aucune i18n correspondant aux locales filtrées.`,
    )
    stats.warnings++
    return
  }

  const existing = await prisma.article.findFirst({
    where: { helpCategoryId: category.id, helpSlug: helpArticle.slug },
    select: { id: true, slug: true },
  })
  if (existing) {
    console.log(
      `  [IDEMPOTENT] HelpArticle ${helpArticle.id} déjà migré → Article ${existing.id} (slug=${existing.slug}). Skip.`,
    )
    stats.alreadyMigrated++
    return
  }

  const localesAvailable = i18nFiltered.map((row) => row.locale)
  const primaryLocale = pickPrimaryLocale(localesAvailable, args.primaryLocale)
  if (!primaryLocale) {
    console.warn(
      `  [SKIP] HelpArticle ${helpArticle.id} : impossible de déterminer la locale primaire (locales disponibles : ${localesAvailable.join(', ')}).`,
    )
    stats.warnings++
    return
  }

  const blocksByLocale = new Map<string, typeof blocksFiltered>()
  for (const b of blocksFiltered) {
    const list = blocksByLocale.get(b.locale) ?? []
    list.push(b)
    blocksByLocale.set(b.locale, list)
  }
  for (const list of blocksByLocale.values()) list.sort((a, b) => a.order - b.order)

  const primaryBlocks = blocksByLocale.get(primaryLocale) ?? []

  for (const row of i18nFiltered) {
    const hasBlocks = (blocksByLocale.get(row.locale) ?? []).length > 0
    const md = (row.contentMarkdown ?? '').trim()
    if (!hasBlocks && md.length > 0) {
      console.warn(
        `  [WARN] HelpArticle ${helpArticle.id} (${row.locale}) : contentMarkdown non vide (${md.length} chars) ` +
          `et aucun HelpArticleBlock pour cette locale. Ce contenu NE SERA PAS migré. ` +
          `Lancer 'migrate-help-markdown-to-blocks.ts --apply' AVANT ce script.`,
      )
      stats.warnings++
    }
  }

  for (const [loc, list] of blocksByLocale) {
    if (loc === primaryLocale) continue
    if (list.length !== primaryBlocks.length) {
      console.warn(
        `  [WARN] HelpArticle ${helpArticle.id} : ${loc} a ${list.length} blocs vs ${primaryLocale}=${primaryBlocks.length}. ` +
          `Mapping par 'order' (les blocs hors index seront ignorés côté i18n).`,
      )
      stats.warnings++
    }
    for (let i = 0; i < Math.min(list.length, primaryBlocks.length); i++) {
      if (list[i].type !== primaryBlocks[i].type) {
        console.warn(
          `  [WARN] HelpArticle ${helpArticle.id} : type mismatch order=${primaryBlocks[i].order} → ` +
            `${primaryLocale}=${primaryBlocks[i].type} ≠ ${loc}=${list[i].type}. Le bloc i18n sera quand même créé.`,
        )
        stats.warnings++
      }
    }
  }

  const baseSlugSeed = `help-${collection.slug}-${category.slug}-${helpArticle.slug}`
  const finalSlug = await ensureUniqueSlug(baseSlugSeed, takenSlugs)

  const articleData: Prisma.ArticleUncheckedCreateInput = {
    slug: finalSlug,
    status: helpArticle.status as ContentStatus,
    publishedAt: helpArticle.publishedAt ?? null,
    createdAt: helpArticle.createdAt,
    updatedAt: helpArticle.updatedAt,
    coverMediaId: helpArticle.coverMediaId ?? null,
    authorName: helpArticle.authorName ?? 'Vancelian',
    authorRole: null,
    allowComments: false,
    coverTitle: null,
    coverCredit: null,
    coverSource: null,
    galleryMediaIds: undefined,
    videoUrl: null,
    categorySlugs: undefined,
    documents: undefined,
    isFeatured: false,
    isHighlighted: false,
    isMilestone: false,
    isCompanyNews: false,
    articleType: 'HELP',
    helpCollectionId: collection.id,
    helpCategoryId: category.id,
    helpSlug: helpArticle.slug,
    allowAnchors: helpArticle.allowAnchors,
    targetTags: (helpArticle.targetTags as Prisma.InputJsonValue | null) ?? undefined,
  }

  const i18nPayloads = i18nFiltered.map((row) => ({
    locale: row.locale,
    title: row.title,
    standfirst: row.standfirst ?? '',
    metaTitle: row.metaTitle ?? null,
    metaDescription: row.metaDescription ?? null,
    coverTitle: null,
    translationStatus: row.translationStatus,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  }))

  const blocksToCreate = primaryBlocks.map((b) => ({
    order: b.order,
    type: b.type,
    data: b.data as Prisma.InputJsonValue,
  }))

  type BlockI18nPayload = { order: number; locale: string; data: Prisma.InputJsonValue; translationStatus: TranslationStatus }
  const blockI18nByOrder: BlockI18nPayload[] = []
  for (const [loc, list] of blocksByLocale) {
    if (loc === primaryLocale) continue
    for (const b of list) {
      const matchPrimary = primaryBlocks.find((p) => p.order === b.order)
      if (!matchPrimary) continue
      blockI18nByOrder.push({
        order: b.order,
        locale: loc,
        data: b.data as Prisma.InputJsonValue,
        translationStatus: TranslationStatus.ORIGINAL,
      })
    }
  }

  console.log(
    `  [PLAN] HelpArticle ${helpArticle.id} → Article (slug=${finalSlug}) | ` +
      `i18n=${i18nPayloads.length} (${i18nPayloads.map((x) => x.locale).join(',')}) | ` +
      `blocks=${blocksToCreate.length} (primary=${primaryLocale}) | ` +
      `block_i18n=${blockI18nByOrder.length}`,
  )
  if (args.verbose) {
    for (const b of blocksToCreate) {
      console.log(`     · block order=${b.order} type=${b.type}`)
    }
  }

  if (!args.apply) {
    stats.migrated++
    stats.blocksCreated += blocksToCreate.length
    stats.blockI18nCreated += blockI18nByOrder.length
    return
  }

  try {
    await prisma.$transaction(async (tx) => {
      const created = await tx.article.create({ data: articleData, select: { id: true } })

      if (i18nPayloads.length > 0) {
        await tx.articleI18n.createMany({
          data: i18nPayloads.map((row) => ({ articleId: created.id, ...row })),
        })
      }

      const orderToBlockId = new Map<number, string>()
      for (const b of blocksToCreate) {
        const createdBlock = await tx.articleBlock.create({
          data: { articleId: created.id, order: b.order, type: b.type, data: b.data },
          select: { id: true, order: true },
        })
        orderToBlockId.set(createdBlock.order, createdBlock.id)
      }

      if (blockI18nByOrder.length > 0) {
        const data = blockI18nByOrder
          .map((row) => {
            const blockId = orderToBlockId.get(row.order)
            if (!blockId) return null
            return {
              blockId,
              locale: row.locale,
              data: row.data,
              translationStatus: row.translationStatus,
            }
          })
          .filter((x): x is { blockId: string; locale: string; data: Prisma.InputJsonValue; translationStatus: TranslationStatus } => x !== null)
        if (data.length > 0) await tx.articleBlockI18n.createMany({ data })
      }
    })
    stats.migrated++
    stats.blocksCreated += blocksToCreate.length
    stats.blockI18nCreated += blockI18nByOrder.length
    console.log(`  [OK]`)
  } catch (err) {
    stats.errors++
    console.error(`  [ERROR] HelpArticle ${helpArticle.id} :`, err instanceof Error ? err.message : err)
  }
}

async function main() {
  const args = parseArgs()
  const mode = args.apply ? 'APPLY (writes)' : 'DRY-RUN (lecture seule)'
  console.log(`\n=== migrate-help-to-article.ts — ${mode} ===\n`)
  if (args.collectionSlug) console.log(`  filtre collection : ${args.collectionSlug}`)
  if (args.categorySlug) console.log(`  filtre catégorie  : ${args.categorySlug}`)
  if (args.locales) console.log(`  filtre locales    : ${args.locales.join(',')}`)
  if (args.primaryLocale) console.log(`  primary-locale    : ${args.primaryLocale}`)
  if (args.limit) console.log(`  limit             : ${args.limit}`)
  console.log()

  const where: Prisma.HelpArticleWhereInput = {}
  if (args.categorySlug || args.collectionSlug) {
    where.category = {}
    if (args.categorySlug) (where.category as Prisma.HelpCategoryWhereInput).slug = args.categorySlug
    if (args.collectionSlug)
      (where.category as Prisma.HelpCategoryWhereInput).collection = { slug: args.collectionSlug }
  }

  const helpArticles = await prisma.helpArticle.findMany({
    where,
    include: {
      category: { include: { collection: true } },
      i18n: true,
      blocks: true,
    },
    orderBy: [{ categoryId: 'asc' }, { slug: 'asc' }],
    take: args.limit ?? undefined,
  })

  const stats: Stats = {
    total: helpArticles.length,
    alreadyMigrated: 0,
    migrated: 0,
    errors: 0,
    warnings: 0,
    blocksCreated: 0,
    blockI18nCreated: 0,
  }

  console.log(`Trouvé ${helpArticles.length} HelpArticle à examiner.\n`)

  const takenSlugs = new Set<string>()
  for (const ha of helpArticles) {
    console.log(
      `→ HelpArticle ${ha.id} | collection=${ha.category.collection.slug} | category=${ha.category.slug} | ` +
        `slug=${ha.slug} | status=${ha.status} | i18n=${ha.i18n.length} | blocks=${ha.blocks.length}`,
    )
    await migrateOne(ha, args, takenSlugs, stats)
  }

  console.log(`\n=== Statistiques ===`)
  console.log(`  Total HelpArticle examinés : ${stats.total}`)
  console.log(`  Déjà migrés (skip)         : ${stats.alreadyMigrated}`)
  console.log(`  Migrés                     : ${stats.migrated}${args.apply ? '' : ' (dry-run, aucune écriture)'}`)
  console.log(`  Erreurs                    : ${stats.errors}`)
  console.log(`  Warnings                   : ${stats.warnings}`)
  console.log(`  ArticleBlock créés         : ${stats.blocksCreated}${args.apply ? '' : ' (dry-run)'}`)
  console.log(`  ArticleBlockI18n créés     : ${stats.blockI18nCreated}${args.apply ? '' : ' (dry-run)'}`)
  console.log()
  if (!args.apply) {
    console.log('Aucune écriture effectuée. Pour persister, relancer avec --apply.')
  }
}

main()
  .catch((err) => {
    console.error('Erreur fatale :', err)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
