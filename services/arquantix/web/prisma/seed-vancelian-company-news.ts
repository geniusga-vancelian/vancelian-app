/**
 * Articles « entreprise » Vancelian (CMS Prisma) + catégories tags (News, License, EU, MENA).
 * Idempotent : skip si les slugs existent déjà.
 */
import { PrismaClient, ArticleBlockType, ContentStatus } from '@prisma/client'

/** Tags blog — news groupe Vancelian + contexte (réglementation, offres, zones). */
const TAG_CATEGORIES: { slug: string; label: string; labelFr: string; order: number }[] = [
  { slug: 'vancelian', label: 'Vancelian', labelFr: 'Vancelian — Actualités entreprise', order: 1 },
  {
    slug: 'corporate-regulatory',
    label: 'Regulation & licences',
    labelFr: 'Réglementation & licences',
    order: 11,
  },
  {
    slug: 'corporate-exclusive',
    label: 'Exclusive offer & real assets',
    labelFr: 'Offre exclusive & actifs réels',
    order: 12,
  },
  { slug: 'news', label: 'News', labelFr: 'News', order: 20 },
  { slug: 'license', label: 'License', labelFr: 'Licence', order: 25 },
  { slug: 'mena', label: 'MENA', labelFr: 'MENA', order: 30 },
  { slug: 'eu', label: 'EU', labelFr: 'UE', order: 35 },
  { slug: 'mica', label: 'MiCA', labelFr: 'MiCA', order: 40 },
  { slug: 'vara', label: 'VARA', labelFr: 'VARA', order: 41 },
  { slug: 'europe', label: 'Europe', labelFr: 'Europe', order: 42 },
  { slug: 'partnership', label: 'Partnership', labelFr: 'Partenariat', order: 43 },
  { slug: 'funding', label: 'Funding', labelFr: 'Levée / financement', order: 44 },
  { slug: 'launch', label: 'Launch', labelFr: 'Lancement', order: 45 },
  { slug: 'regulation', label: 'Regulation', labelFr: 'Réglementation', order: 46 },
  { slug: 'm-and-a', label: 'M&A', labelFr: 'Fusion & acquisition', order: 47 },
]

async function ensureArticleCategories(db: PrismaClient) {
  for (const c of TAG_CATEGORIES) {
    await db.articleCategory.upsert({
      where: { slug: c.slug },
      update: { label: c.label, order: c.order },
      create: {
        slug: c.slug,
        label: c.label,
        order: c.order,
        i18n: {
          create: {
            locale: 'fr',
            label: c.labelFr,
          },
        },
      },
    })
    const row = await db.articleCategory.findUnique({ where: { slug: c.slug } })
    if (row) {
      await db.articleCategoryI18n.upsert({
        where: {
          categoryId_locale: { categoryId: row.id, locale: 'fr' },
        },
        update: { label: c.labelFr },
        create: {
          categoryId: row.id,
          locale: 'fr',
          label: c.labelFr,
        },
      })
    }
  }
}

function paragraphBlock(order: number, text: string) {
  return {
    order,
    type: ArticleBlockType.PARAGRAPH,
    data: { text },
    i18n: {
      create: {
        locale: 'fr',
        data: { text },
      },
    },
  }
}

function headingBlock(order: number, text: string) {
  return {
    order,
    type: ArticleBlockType.HEADING,
    data: { text },
    i18n: {
      create: {
        locale: 'fr',
        data: { text },
      },
    },
  }
}

function bulletBlock(order: number, items: string[]) {
  const data = { items }
  return {
    order,
    type: ArticleBlockType.BULLET_LIST,
    data,
    i18n: {
      create: {
        locale: 'fr',
        data,
      },
    },
  }
}

export async function seedVancelianCompanyNews(db: PrismaClient) {
  await ensureArticleCategories(db)

  const slugVara = 'vancelian-obtient-le-in-principle-approval-de-vara'
  if (!(await db.article.findUnique({ where: { slug: slugVara } }))) {
    await db.article.create({
      data: {
        slug: slugVara,
        status: ContentStatus.PUBLISHED,
        publishedAt: new Date('2026-04-01T10:00:00.000Z'),
        authorName: 'Vancelian',
        authorRole: 'Communication',
        articleType: 'NEWS',
        isFeatured: false,
        isHighlighted: true,
        categorySlugs: ['vancelian', 'corporate-regulatory', 'license', 'mena'],
        i18n: {
          create: {
            locale: 'fr',
            title: 'Vancelian obtient le In-Principle Approval de VARA',
            standfirst:
              'Vancelian (Automata FZE) franchit une étape clé du parcours réglementaire à Dubaï avec un IPA délivré par VARA.',
          },
        },
        blocks: {
          create: [
            paragraphBlock(
              0,
              'Nous sommes heureux de confirmer que Vancelian (Automata FZE) a obtenu son In-Principle Approval (IPA) délivré par la Virtual Assets Regulatory Authority (VARA) de Dubaï, pour les catégories d’activités suivantes :',
            ),
            bulletBlock(1, [
              'Broker Dealer',
              'Management & Investments',
              'Lending & Borrowing',
              'Advisory',
            ]),
            paragraphBlock(
              2,
              'Cette étape constitue une avancée majeure dans le parcours réglementaire de Vancelian et reflète la solidité de son cadre de gouvernance, la clarté de sa vision stratégique de long terme, ainsi que l’engagement de ses équipes en faveur d’un développement responsable, conforme et durable au sein de l’écosystème des actifs numériques.',
            ),
            paragraphBlock(
              3,
              'À la suite de l’obtention de cet In-Principle Approval, Vancelian poursuit désormais la prochaine phase du processus réglementaire, avec pour objectif l’obtention de la licence définitive délivrée par VARA, condition préalable au démarrage des activités réglementées aux Émirats arabes unis.',
            ),
            paragraphBlock(
              4,
              'Vancelian remercie VARA pour la qualité des échanges tout au long de ce processus, ainsi que W3C, son cabinet de conseil réglementaire, pour son accompagnement continu.',
            ),
            headingBlock(5, 'Mention réglementaire'),
            paragraphBlock(
              6,
              'L’In-Principle Approval ne constitue pas une licence définitive. Vancelian ne pourra démarrer ses activités réglementées aux Émirats arabes unis qu’après l’obtention de l’autorisation finale de VARA.',
            ),
          ],
        },
      },
    })
    console.log(`  ✅ Article entreprise créé : ${slugVara}`)
  } else {
    console.log(`  ℹ️  Article déjà présent : ${slugVara}`)
  }

  const slugDubai =
    'vancelian-mise-sur-les-actifs-reels-pour-rapprocher-finance-traditionnelle-et-crypto-et-lance-sa-seconde-offre-exclusive-avec-un-projet-immobilier-a-dubai-1'
  if (!(await db.article.findUnique({ where: { slug: slugDubai } }))) {
    await db.article.create({
      data: {
        slug: slugDubai,
        status: ContentStatus.PUBLISHED,
        publishedAt: new Date('2026-03-15T10:00:00.000Z'),
        authorName: 'Vancelian',
        authorRole: 'Communication',
        articleType: 'NEWS',
        isFeatured: false,
        isHighlighted: true,
        categorySlugs: ['vancelian', 'corporate-exclusive', 'mena', 'eu'],
        i18n: {
          create: {
            locale: 'fr',
            title:
              'Vancelian mise sur les actifs réels et lance une seconde Offre Exclusive à Dubaï',
            standfirst:
              'Après Bali, la fintech ouvre un projet immobilier à Dubaï (Al Barari) pour rapprocher finance traditionnelle et crypto-actifs.',
          },
        },
        blocks: {
          create: [
            paragraphBlock(
              0,
              'La fintech française Vancelian poursuit sa stratégie de démocratisation de l’investissement en lançant une nouvelle offre centrée sur les actifs réels. Après le succès d’un premier projet immobilier à Bali, l’entreprise présente une seconde opportunité à Dubaï, misant sur la blockchain et les crypto-actifs pour ouvrir l’accès à des placements jusqu’ici réservés à une élite.',
            ),
            headingBlock(1, 'Une vision claire : rendre les investissements premium accessibles à tous'),
            paragraphBlock(
              2,
              'Depuis Sophia-Antipolis, Vancelian développe une approche innovante du co-financement en actifs numériques, permettant aux investisseurs de participer à des projets d’acquisition ou de rénovation d’actifs tangibles – notamment dans l’immobilier – tout en percevant un rendement.',
            ),
            paragraphBlock(
              3,
              'Cette stratégie allie diversification patrimoniale, sécurité réglementaire et simplicité d’accès grâce à l’application Vancelian, enregistrée auprès de l’AMF. L’objectif est simple : supprimer les barrières d’entrée qui limitaient jusqu’ici l’accès aux investissements de qualité institutionnelle.',
            ),
            headingBlock(4, 'Citation'),
            paragraphBlock(
              5,
              '« Notre innovation repose sur la possibilité d’investir sans ticket d’entrée minimum dans des projets jusqu’alors réservés aux grands investisseurs. C’est une promesse forte, à l’heure où la frontière entre finance traditionnelle et crypto-actifs s’estompe. » — Gaël Itier, CEO et co-fondateur de Vancelian.',
            ),
            headingBlock(6, 'Bali, un premier terrain d’expérimentation concluant'),
            paragraphBlock(
              7,
              'Vancelian a inauguré sa gamme d’Offres Exclusives avec le financement de sept villas de prestige à Bali. Les investisseurs ont participé à l’opération via un prêt en cryptomonnaie adossé au Bitcoin, avec un rendement fixe communiqué selon les conditions de l’offre et le programme Privilège, et un versement quotidien des intérêts pour une liquidité renforcée.',
            ),
            headingBlock(8, 'Cap sur Dubaï — The Nest, Al Barari'),
            paragraphBlock(
              9,
              'La seconde opération porte sur l’acquisition et la rénovation d’une villa de prestige dans l’un des quartiers les plus verdoyants et exclusifs de Dubaï, Al Barari. L’objectif : associer innovation financière, rendement et rareté immobilière au cœur d’une destination prisée de l’investissement patrimonial.',
            ),
            paragraphBlock(
              10,
              'Fruit du savoir-faire Vancelian, ce modèle de co-financement en actif numérique offre une opportunité d’allier rendement, exclusivité et simplicité d’accès dans la gestion de votre patrimoine.',
            ),
            headingBlock(11, 'Un marché en plein essor : la tokenisation des actifs réels'),
            paragraphBlock(
              12,
              'La tokenisation permet de fractionner la propriété de biens réels, élargissant l’accès à des investissements autrefois limités aux fortunes les plus élevées. La capacité de Vancelian à anticiper les grandes tendances de la finance numérique se traduit aujourd’hui par des solutions de prêt en cryptomonnaie ; demain, par la maîtrise de la chaîne de valeur de la tokenisation d’actifs réels.',
            ),
          ],
        },
      },
    })
    console.log(`  ✅ Article entreprise créé : ${slugDubai}`)
  } else {
    console.log(`  ℹ️  Article déjà présent : ${slugDubai}`)
  }

  const companyTagsBySlug: Record<string, string[]> = {
    [slugVara]: ['vancelian', 'corporate-regulatory', 'license', 'mena'],
    [slugDubai]: ['vancelian', 'corporate-exclusive', 'mena', 'eu'],
  }
  for (const [slug, tags] of Object.entries(companyTagsBySlug)) {
    const row = await db.article.findUnique({ where: { slug } })
    if (row) {
      await db.article.update({
        where: { slug },
        data: { categorySlugs: tags },
      })
      console.log(`  ✅ Tags entreprise Vancelian synchronisés : ${slug}`)
    }
  }
}
