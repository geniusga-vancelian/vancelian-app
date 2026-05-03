/**
 * Crée 15 articles de blog publiés avec couvertures tirées au hasard dans `media`.
 *
 * Usage : npx tsx scripts/seed-random-blog-articles.ts
 *
 * Slugs : `seed-random-blog-<timestamp>-<n>` — repérables pour nettoyage manuel.
 */

import { PrismaClient, ContentStatus, ArticleBlockType } from '@prisma/client'

const prisma = new PrismaClient()

const SUBJECTS = [
  'Marchés',
  'Régulation',
  'Tokenisation',
  'Immobilier',
  'DeFi',
  'Institutionnels',
  'ESG',
  'Infrastructure',
  'Stablecoins',
  'MENA',
  'Europe',
  'Données on-chain',
]

const ANGLES = [
  'tendances à surveiller',
  'ce qui change en 2026',
  'analyse et perspectives',
  'retour sur les annonces clés',
  'focus réglementaire',
  'decryptage pour investisseurs',
  'points de vigilance',
  'opportunités et risques',
]

const STANDFIRSTS = [
  'Synthèse rapide des facteurs qui structurent le paysage cette saison.',
  'Les équipes décryptent les signaux récents et ce qu’ils impliquent pour les portefeuilles.',
  'Un tour d’horizon des évolutions techniques, juridiques et de marché.',
  'Ce billet met en perspective les lectures court terme et long terme.',
  'Éléments de langage et repères pour suivre la suite du dossier.',
]

const PARAS = [
  'Les acteurs institutionnels continuent d’affiner leur exposition tout en renforçant la gouvernance et la transparence des processus.',
  'La liquidité et la profondeur de marché restent des critères centraux lorsque l’on compare les différentes infrastructures.',
  'Les cadres réglementaires évoluent ; il convient de distinguer annonces, consultations et textes définitivement applicables.',
  'Côté technologie, l’interopérabilité et la sécurisation des parcours utilisateurs gagnent en maturité.',
  'Pour les investisseurs, la diversification et la compréhension des contreparties demeurent des piliers incontournables.',
]

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]!
}

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j]!, a[i]!]
  }
  return a
}

function paragraphBlock(order: number, text: string) {
  const data = { text }
  return {
    order,
    type: ArticleBlockType.PARAGRAPH,
    data,
    i18n: {
      create: {
        locale: 'fr',
        data,
      },
    },
  }
}

async function main() {
  let mediaRows = await prisma.media.findMany({
    where: {
      mimeType: { startsWith: 'image/' },
      NOT: { mimeType: { in: ['image/svg+xml'] } },
    },
    select: { id: true, filename: true },
  })

  if (mediaRows.length === 0) {
    mediaRows = await prisma.media.findMany({
      where: { NOT: { mimeType: { in: ['image/svg+xml'] } } },
      select: { id: true, filename: true },
    })
  }

  if (mediaRows.length === 0) {
    console.error('Aucun média en base : importez des images avant de lancer ce script.')
    process.exit(1)
  }

  const pool = shuffle(mediaRows)
  const runId = Date.now()
  const count = 15

  console.log(`Médias images disponibles : ${mediaRows.length}. Création de ${count} articles (run ${runId})…`)

  for (let i = 0; i < count; i++) {
    const slug = `seed-random-blog-${runId}-${i + 1}`
    const exists = await prisma.article.findUnique({ where: { slug } })
    if (exists) {
      console.log(`  Skip (existe déjà) : ${slug}`)
      continue
    }

    const cover = pool[i % pool.length]!
    const title = `${pick(SUBJECTS)} : ${pick(ANGLES)}`
    const standfirst = pick(STANDFIRSTS)
    const publishedAt = new Date(Date.now() - (i + 1) * 3_600_000 * (1 + Math.floor(Math.random() * 8)))

    await prisma.article.create({
      data: {
        slug,
        status: ContentStatus.PUBLISHED,
        publishedAt,
        coverMediaId: cover.id,
        authorName: pick(['Rédaction', 'Studio éditorial', 'Contributions invitées']),
        authorRole: Math.random() > 0.35 ? pick(['Analyse', 'Marchés', 'Régulation']) : null,
        articleType: Math.random() > 0.75 ? 'ANALYSIS' : 'NEWS',
        isFeatured: false,
        isHighlighted: Math.random() > 0.85,
        isCompanyNews: Math.random() > 0.9,
        categorySlugs: Math.random() > 0.5 ? ['crypto'] : ['vancelian'],
        i18n: {
          create: {
            locale: 'fr',
            title,
            standfirst,
          },
        },
        blocks: {
          create: [
            paragraphBlock(0, pick(PARAS)),
            paragraphBlock(1, pick(PARAS)),
            paragraphBlock(2, pick(PARAS)),
          ],
        },
      },
    })

    console.log(`  ✅ ${slug} ← cover: ${cover.filename}`)
  }

  console.log('Terminé.')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
