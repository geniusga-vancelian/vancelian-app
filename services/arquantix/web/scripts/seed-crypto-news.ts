import { ContentStatus, PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

type CryptoNewsSeed = {
  slug: string
  title: string
  standfirst: string
  paragraph: string
}

const AUTHOR_NAME = 'Arquantix Research Desk'

const CRYPTO_NEWS: CryptoNewsSeed[] = [
  {
    slug: 'btc-rebond-69k-espoir-diplomatique-2026-04-07',
    title:
      'Bitcoin au-dessus de 69 000 $ : rebond des actifs à risque sur fond d’espoir diplomatique',
    standfirst:
      'Le 7 avril 2026, le BTC a effacé une partie des pertes matinales, dans le sillage des marchés actions, alors que les investisseurs suivaient les développements au Moyen-Orient.',
    paragraph:
      'Les cours ont oscillé après une ouverture en nette baisse, puis le Bitcoin a retrouvé des niveaux supérieurs à 69 000 dollars US sur plusieurs agrégats, au même moment où les indices « risk-on » repassaient dans le vert. Ce mouvement coïncidait avec des signaux d’ouverture sur un apaisement des tensions géopolitiques évoqués dans la presse financière internationale ce jour-là.\n\n' +
      'Synthèse rédigée pour l’app à partir de dépêches publiques (ex. CoinDesk, Yahoo Finance, 7 avril 2026). À croiser avec votre flux temps réel avant toute décision d’investissement.',
  },
  {
    slug: 'crypto-news-bitcoin-repasse-70k-etf-spot',
    title: 'Bitcoin repasse les 70 000$ sur fond de flux ETF spot en hausse',
    standfirst:
      'Les volumes sur les ETF spot augmentent pour la troisieme semaine consecutive, soutenant un retour de volatilite sur le marche crypto.',
    paragraph:
      'Le mouvement est principalement porte par des rachats institutionnels progressifs, combines a une offre toujours contrainte sur les plateformes de reference.',
  },
  {
    slug: 'crypto-news-ethereum-l2-adoption-entreprises',
    title: 'Ethereum: l adoption des couches L2 accelere cote entreprises',
    standfirst:
      'De nouveaux cas d usage B2B apparaissent autour des L2, avec un focus sur la reduction des couts de transaction et la finalite rapide.',
    paragraph:
      'Les equipes techniques privilegient des integrations hybrides, conservant des process off-chain tout en ancrant les preuves critiques sur Ethereum.',
  },
  {
    slug: 'crypto-news-solana-retour-ecosysteme-defi',
    title: 'Solana confirme son retour avec une reprise de l activite DeFi',
    standfirst:
      'La TVL et les transactions quotidiennes progressent, signe d un regain d interet pour l ecosysteme et ses applications orientees grand public.',
    paragraph:
      'Les protocoles majeurs mettent en avant des executions plus fluides et des frais reduits, ce qui stimule les arbitrages cross-chain.',
  },
  {
    slug: 'crypto-news-tokenisation-actifs-reels-progresse',
    title: 'La tokenisation d actifs reels poursuit sa progression en Europe',
    standfirst:
      'Plusieurs initiatives pilote confirment une traction sur les obligations, fonds prives et produits structures tokenises.',
    paragraph:
      'Les acteurs financiers recherchent surtout des gains operationnels: meilleure traçabilite, settlement simplifie et distribution plus flexible.',
  },
  {
    slug: 'crypto-news-stablecoins-regulation-ue-etapes',
    title: 'Stablecoins: nouvelles etapes de mise en conformite dans l UE',
    standfirst:
      'Les emetteurs adaptent leur gouvernance et leurs reserves pour s aligner avec les exigences reglementaires europeennes.',
    paragraph:
      'Le marche distingue de plus en plus les stablecoins selon la transparence des reserves, la liquidite et la qualite des procedures de controle.',
  },
  {
    slug: 'crypto-news-rwa-protocoles-croissance-selective',
    title: 'RWA: croissance selective des protocoles exposes a la dette privee',
    standfirst:
      'Les rendements proposes attirent de nouveaux profils d investisseurs, mais la selection des contreparties reste determinante.',
    paragraph:
      'Les plateformes qui publient des reportings frequents et des politiques de risque lisibles captent l essentiel des nouveaux flux.',
  },
  {
    slug: 'crypto-news-btc-volatilite-implicite-remonte',
    title: 'Options BTC: la volatilite implicite remonte avant les publications macro',
    standfirst:
      'Le marche des options anticipe des variations plus larges autour des prochains indicateurs economiques americains.',
    paragraph:
      'Les desks preferent des structures defensives avec couverture progressive, en attendant une direction plus claire sur les taux.',
  },
  {
    slug: 'crypto-news-defi-risque-contrepartie-surveillance',
    title: 'DeFi: le risque de contrepartie revient au centre de la surveillance',
    standfirst:
      'Apres plusieurs incidents isoles, les investisseurs renforcent leurs criteres de due diligence sur les protocoles de credit.',
    paragraph:
      'Les metriques de collaterisation, la qualite des oracles et les mecanismes de liquidation deviennent les points de controle prioritaires.',
  },
  {
    slug: 'crypto-news-ia-et-trading-onchain-nouveaux-usages',
    title: 'IA et trading on-chain: les nouveaux usages se structurent',
    standfirst:
      'Des outils d aide a la decision en temps reel se democratisent, avec des tableaux de bord combines market data et signaux on-chain.',
    paragraph:
      'La valeur se deplace vers la qualite des donnees et la robustesse des modeles, plus que vers la simple automatisation d ordres.',
  },
  {
    slug: 'crypto-news-marche-crypto-correlation-actions-tech',
    title: 'Marche crypto: correlation plus stable avec les actions technologiques',
    standfirst:
      'Les actifs numeriques montrent une sensibilite accrue aux annonces de politique monetaire et aux mouvements du secteur tech.',
    paragraph:
      'Dans ce contexte, les allocations tactiques privilegient des entrees echelonnees et une gestion stricte du risque de drawdown.',
  },
]

async function ensureCryptoCategory() {
  const category = await prisma.articleCategory.upsert({
    where: { slug: 'crypto' },
    update: {
      label: 'Crypto',
      isActive: true,
    },
    create: {
      slug: 'crypto',
      label: 'Crypto',
      order: 50,
      isActive: true,
    },
  })

  await prisma.articleCategoryI18n.upsert({
    where: {
      categoryId_locale: {
        categoryId: category.id,
        locale: 'fr',
      },
    },
    update: { label: 'Crypto' },
    create: {
      categoryId: category.id,
      locale: 'fr',
      label: 'Crypto',
    },
  })

  await prisma.articleCategoryI18n.upsert({
    where: {
      categoryId_locale: {
        categoryId: category.id,
        locale: 'en',
      },
    },
    update: { label: 'Crypto' },
    create: {
      categoryId: category.id,
      locale: 'en',
      label: 'Crypto',
    },
  })
}

async function upsertCryptoNewsArticles() {
  let createdOrUpdated = 0
  const now = Date.now()

  for (let i = 0; i < CRYPTO_NEWS.length; i += 1) {
    const item = CRYPTO_NEWS[i]
    const publishedAt = new Date(now - i * 24 * 60 * 60 * 1000)

    const article = await prisma.article.upsert({
      where: { slug: item.slug },
      update: {
        status: ContentStatus.PUBLISHED,
        publishedAt,
        authorName: AUTHOR_NAME,
        articleType: 'NEWS',
        categorySlugs: ['crypto'],
        isFeatured: false,
        isHighlighted: false,
        isMilestone: false,
      },
      create: {
        slug: item.slug,
        status: ContentStatus.PUBLISHED,
        publishedAt,
        authorName: AUTHOR_NAME,
        articleType: 'NEWS',
        categorySlugs: ['crypto'],
        isFeatured: false,
        isHighlighted: false,
        isMilestone: false,
      },
      select: { id: true },
    })

    await prisma.articleI18n.upsert({
      where: {
        articleId_locale: {
          articleId: article.id,
          locale: 'fr',
        },
      },
      update: {
        title: item.title,
        standfirst: item.standfirst,
      },
      create: {
        articleId: article.id,
        locale: 'fr',
        title: item.title,
        standfirst: item.standfirst,
      },
    })

    await prisma.articleBlock.upsert({
      where: {
        articleId_order: {
          articleId: article.id,
          order: 0,
        },
      },
      update: {
        type: 'HEADING',
        data: { text: item.title, level: 2 },
      },
      create: {
        articleId: article.id,
        order: 0,
        type: 'HEADING',
        data: { text: item.title, level: 2 },
      },
    })

    await prisma.articleBlock.upsert({
      where: {
        articleId_order: {
          articleId: article.id,
          order: 1,
        },
      },
      update: {
        type: 'PARAGRAPH',
        data: { text: item.paragraph },
      },
      create: {
        articleId: article.id,
        order: 1,
        type: 'PARAGRAPH',
        data: { text: item.paragraph },
      },
    })

    createdOrUpdated += 1
  }

  return createdOrUpdated
}

async function main() {
  await ensureCryptoCategory()
  const count = await upsertCryptoNewsArticles()
  console.log(`Crypto news seed complete: ${count} articles upserted.`)
}

main()
  .catch((error) => {
    console.error('Crypto news seed failed:', error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
