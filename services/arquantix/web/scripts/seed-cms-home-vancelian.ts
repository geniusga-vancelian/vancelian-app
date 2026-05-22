/**
 * Seed homepage Vancelian (contenu + médias de `Home.html` du pack DS).
 *
 * Prérequis :
 * - ZIP extrait ou présent dans ~/Downloads/home.zip
 * - DATABASE_URL accessible
 *
 * Exécution :
 *   cd services/arquantix/web && npx tsx scripts/seed-cms-home-vancelian.ts
 */

import fs from 'node:fs'
import path from 'node:path'
import { PrismaClient, ContentStatus, Prisma } from '@prisma/client'

const prisma = new PrismaClient()

const PAGE_SLUG = 'home'
const ZIP_ROOT =
  process.env.VANCELIAN_HOME_ZIP_ROOT ||
  '/tmp/home-zip/export-home'
const PUBLIC_MEDIA_DIR = path.join(process.cwd(), 'public/cms/vancelian-home')

type MediaRef = { id: string; url: string }

async function ensureLocalMedia(opts: {
  key: string
  srcPath: string
  filename: string
  mimeType: string
  alt?: string
}): Promise<MediaRef> {
  if (!fs.existsSync(opts.srcPath)) {
    throw new Error(`Fichier média introuvable : ${opts.srcPath}`)
  }
  fs.mkdirSync(PUBLIC_MEDIA_DIR, { recursive: true })
  const destPath = path.join(PUBLIC_MEDIA_DIR, opts.filename)
  if (!fs.existsSync(destPath)) {
    fs.copyFileSync(opts.srcPath, destPath)
  }
  const stat = fs.statSync(destPath)
  const url = `/cms/vancelian-home/${opts.filename}`
  const media = await prisma.media.upsert({
    where: { key: opts.key },
    update: {
      url,
      filename: opts.filename,
      mimeType: opts.mimeType,
      size: stat.size,
      alt: opts.alt ?? null,
    },
    create: {
      key: opts.key,
      url,
      filename: opts.filename,
      mimeType: opts.mimeType,
      size: stat.size,
      alt: opts.alt ?? null,
    },
  })
  return { id: media.id, url }
}

async function seedMedia(): Promise<Record<string, MediaRef>> {
  const base = ZIP_ROOT
  const files: Array<{ name: string; key: string; rel: string; mime: string; alt?: string }> = [
    { name: 'hero-bg.mp4', key: 'cms/vancelian-home/hero-bg.mp4', rel: 'assets/hero-bg.mp4', mime: 'video/mp4', alt: 'Hero background' },
    { name: 'niseko.mp4', key: 'cms/vancelian-home/niseko.mp4', rel: 'uploads/niseko-f46cbf38.mp4', mime: 'video/mp4' },
    { name: 'dubai.mp4', key: 'cms/vancelian-home/dubai.mp4', rel: 'uploads/dubai-ac537438.mp4', mime: 'video/mp4' },
    { name: 'bali.mp4', key: 'cms/vancelian-home/bali.mp4', rel: 'uploads/bali-692b8213.mp4', mime: 'video/mp4' },
    { name: 'aerial-boats.mp4', key: 'cms/vancelian-home/aerial-boats.mp4', rel: 'uploads/aerial-boats.mp4', mime: 'video/mp4' },
    { name: 'apartment-old.mp4', key: 'cms/vancelian-home/apartment-old.mp4', rel: 'uploads/apartment-old.mp4', mime: 'video/mp4' },
    { name: 'smartphone-mockup.mp4', key: 'cms/vancelian-home/smartphone-mockup.mp4', rel: 'uploads/smartphone-mockup.mp4', mime: 'video/mp4' },
  ]

  const out: Record<string, MediaRef> = {}
  for (const f of files) {
    out[f.name] = await ensureLocalMedia({
      key: f.key,
      srcPath: path.join(base, f.rel),
      filename: f.name,
      mimeType: f.mime,
      alt: f.alt,
    })
    console.log(`  media ${f.name} → ${out[f.name].id}`)
  }
  return out
}

function buildSections(media: Record<string, MediaRef>): Array<{ key: string; order: number; data: Prisma.InputJsonObject }> {
  return [
    {
      key: 'hero',
      order: 0,
      data: {
        eyebrow: 'Patrimoine tokenisé',
        title: 'Bâtir son\npatrimoine,',
        typewriterWords: ['aujourd\'hui', 'en famille', 'à plusieurs', 'en crypto', 'en immobilier'],
        subtitle:
          'Immobilier premium tokenisé, épargne flexible, cryptomonnaies. Le tout depuis une seule application.',
        inlineStats: ['500K téléchargements', '100 M€ sous gestion', '7 M€ d\'intérêts versés'],
        ctaText: 'Télécharger l\'app',
        ctaLink: '#download-app',
        secondaryCtaText: 'Découvrir les offres',
        secondaryCtaHref: '/fr/offres-exclusives',
        note: 'Note moyenne 4,6 ★ basée sur 1 600+ avis',
        backgroundMediaId: media['hero-bg.mp4'].id,
        backgroundImageOpacity: 1,
      },
    },
    {
      key: 'proof_press',
      order: 1,
      data: {
        eyebrow: 'Ils parlent de nous',
        items: [
          { label: 'BFM BUSINESS', variant: 'bfm' },
          { label: 'La Tribune', variant: 'tribune' },
          { label: 'Les Échos', variant: 'echos' },
          { label: 'FINYEAR', variant: 'finyear' },
        ],
      },
    },
    {
      key: 'offer_cards',
      order: 2,
      data: {
        eyebrow: 'Offres exclusives',
        title: 'L\'immobilier premium,\nfragment par fragment.',
        description:
          'Investissez dans des projets immobiliers haut de gamme tokenisés. À partir de 100 €. Liquidité possible à tout moment.',
        viewAllButtonText: 'Voir toutes les offres',
        viewAllButtonHref: '/fr/offres-exclusives',
        items: [
          {
            ariaLabel: 'Niseko Mori Lodge — Japon',
            centerText: 'La beauté du <em>Japon</em>',
            barTitle: 'Niseko Mori Lodge',
            barSubtitle: 'Japon · Funded 30%',
            barRate: '9–12,5%',
            hoverVideoMediaId: media['niseko.mp4'].id,
            href: '/fr/offres-exclusives',
          },
          {
            ariaLabel: 'Dubai Al Barari — Émirats',
            centerText: 'L\'exclusivité de <em>Dubai</em>',
            barTitle: 'Dubai Al Barari',
            barSubtitle: 'Émirats · Ouverte',
            barRate: '8–11%',
            hoverVideoMediaId: media['dubai.mp4'].id,
            href: '/fr/offres-exclusives',
          },
          {
            ariaLabel: 'Bali Luxury Resort — Indonésie',
            centerText: 'L\'exotisme de <em>Bali</em>',
            barTitle: 'Bali Luxury Resort',
            barSubtitle: 'Indonésie · Funded 100%',
            barRate: '7–9%',
            hoverVideoMediaId: media['bali.mp4'].id,
            href: '/fr/offres-exclusives',
          },
        ],
      },
    },
    {
      key: 'product_ecosystem',
      order: 3,
      data: {
        title: 'Au-delà <em>de l\'immobilier.</em>',
        description:
          'Votre patrimoine ne se limite pas à un actif. Vancelian regroupe épargne flexible, cryptomonnaies sélectionnées et carte de paiement dans une seule application.',
        items: [
          {
            iconName: 'wallet',
            title: 'Coffres d\'épargne adapté à vos besoins',
            description: 'Faites travailler votre cash sans le bloquer. Intérêts versés quotidiennement, retrait sous 24h.',
            features: [
              { text: 'Rendement actuel jusqu\'à 6,44 %' },
              { text: 'Disponibilité immédiate' },
              { text: 'À partir de 1 €' },
            ],
            linkText: 'Découvrir l\'épargne',
            linkHref: '/fr/epargne',
          },
          {
            iconName: 'bitcoin',
            title: 'Cryptomonnaies séléctionnées',
            description: 'Investissez dans un panier des principales cryptos ou choisissez vos actifs. Sans frais cachés.',
            features: [
              { text: 'Top 5 ou Top 2 prêts à l\'emploi' },
              { text: 'Frais 1 % par transaction' },
              { text: 'Conservation sécurisée' },
            ],
            linkText: 'Découvrir les cryptos',
            linkHref: '/fr/crypto',
          },
          {
            iconName: 'credit-card',
            title: 'Compte IBAN & Carte Visa physique',
            description: 'Payez avec ce que vous avez gagné. Cashback sur toutes vos dépenses, en France et à l\'international.',
            features: [
              { text: '0 % de commission de change' },
              { text: 'Cashback automatique' },
              { text: 'Compatible Apple Pay et Google Pay' },
            ],
            linkText: 'Découvrir la carte',
            linkHref: '/fr/carte',
          },
        ],
      },
    },
    {
      key: 'journey_01',
      order: 4,
      data: {
        pill: 'Étape 01',
        title: 'Nous choisissons <em>l\'actif.</em>',
        description:
          'Moins de 5 % des dossiers étudiés sont retenus. Notre équipe immobilière audite chaque emplacement, chaque opérateur, chaque structure juridique avant ouverture.',
        backgroundMediaId: media['aerial-boats.mp4'].id,
        notificationMessage: 'Niseko Mori Lodge ouvre demain à 18 h.',
        ctas: [{ label: 'Notre processus de sélection', href: '/fr/processus', variant: 'secondary' }],
      },
    },
    {
      key: 'journey_02',
      order: 5,
      data: {
        pill: 'Étape 02',
        title: 'L\'actif devient <em>fragmentable.</em>',
        description:
          'Chaque projet est porté par un SPV dédié. Les parts sont émises en tokens ERC-1400. Accessible à partir de quelques centaines d\'euros, avec la liquidité d\'un marché secondaire interne.',
        backgroundMediaId: media['apartment-old.mp4'].id,
        notificationMessage: 'Vos 24 parts viennent d\'être émises.',
        ctas: [
          { label: 'Investir maintenant', href: '/fr/offres-exclusives', variant: 'primary' },
          { label: 'Comprendre la tokenisation', href: '/fr/tokenisation', variant: 'secondary' },
        ],
      },
    },
    {
      key: 'journey_03',
      order: 6,
      data: {
        pill: 'Étape 03',
        title: 'Vous récoltez, <em>trimestre après trimestre.</em>',
        description:
          'Les revenus locatifs nets sont distribués proportionnellement à vos parts, chaque trimestre, directement sur votre wallet Vancelian. Disponibles à tout moment.',
        backgroundMediaId: media['smartphone-mockup.mp4'].id,
        notificationMessage: 'Distribution Q2 reçue · +412 € sur votre wallet.',
        ctas: [{ label: 'Voir un exemple de distribution', href: '/fr/exemple-distribution', variant: 'secondary' }],
      },
    },
    {
      key: 'figma_testimonial_cards',
      order: 7,
      data: {
        title: 'Investisseurs avant\n<em>d\'être clients.</em>',
        description: 'Note moyenne 4,6 ★ basée sur 1 600+ avis sur les stores et plateformes de notation.',
        cardsPerRow: 2,
        items: [
          {
            author: 'Julien D.',
            role: 'Cadre dirigeant · Lyon',
            content:
              '« J\'utilise Vancelian depuis 2 ans pour diversifier mon épargne. Les rendements sont au rendez-vous, et la transparence sur les frais m\'a vraiment surpris en bien. »',
          },
          {
            author: 'Yvan M.',
            role: 'Entrepreneur · Paris',
            content:
              '« Ce qui m\'a convaincu, c\'est l\'accès à des projets immobiliers que je n\'aurais jamais pu intégrer seul. Les offres exclusives sont vraiment exclusives. »',
          },
          {
            author: 'Elodie R.',
            role: 'Architecte · Marseille',
            content:
              '« L\'application est claire, même pour quelqu\'un comme moi qui n\'avais jamais investi. Le KYC s\'est fait en 10 minutes, mon premier dépôt en 2 minutes. »',
          },
          {
            author: 'Sofia L.',
            role: 'Consultante · Bordeaux',
            content:
              '« Le support est réactif, les chiffres sont nets, et surtout je peux retirer quand je veux. Ce qui n\'est jamais le cas en immobilier classique. »',
          },
        ],
      },
    },
    {
      key: 'security',
      order: 8,
      data: {
        title: 'Régulé, audité,\n<em>transparent.</em>',
        description:
          'Vancelian opère dans un cadre régulé strict. Vos actifs sont ségrégués chez nos partenaires bancaires. Vos données sont chiffrées de bout en bout. Nos comptes sont audités annuellement par un cabinet indépendant.',
        points: [
          { text: 'Enregistré PSAN auprès de l\'AMF' },
          { text: 'Partenariat bancaire Modulr (FCA / ACPR)' },
          { text: 'Audit annuel cabinet Big Four' },
        ],
        linkText: 'Lire le rapport sécurité',
        linkHref: '/fr/securite',
        logos: [
          { label: 'AMF', caption: 'Enregistrement PSAN' },
          { label: 'Modulr', caption: 'Partenaire bancaire' },
          { label: 'VISA', caption: 'Émetteur de la carte' },
          { label: 'Audit', caption: 'Audit annuel' },
        ],
      },
    },
    {
      key: 'faq',
      order: 9,
      data: {
        eyebrow: 'QUESTIONS FRÉQUENTES',
        title: "L'essentiel\n<em>en bref.</em>",
        description: '',
        support: {
          title: 'Une question ?',
          description: 'Notre équipe répond aux questions techniques sous 24 h.',
          ctaLabel: 'Contacter le support →',
          ctaHref: '/fr/contact',
          secondaryLinkLabel: 'FAQ complète →',
          secondaryLinkHref: '/fr/aide',
        },
        items: [
          {
            id: 'faq-regulation',
            question: 'Vancelian est-il régulé ?',
            answerMarkdown:
              'Oui. Vancelian est enregistré comme PSAN auprès de l\'AMF sous le numéro E2023-087. Nos opérations sont conformes au règlement européen MiCA.',
          },
          {
            id: 'faq-fees',
            question: 'Quels sont les frais ?',
            answerMarkdown:
              'Aucun frais d\'abonnement. L\'immobilier tokenisé comporte 1 % de frais d\'entrée et 0,5 % de frais de gestion annuels. Les transactions crypto sont facturées à 1 %.',
          },
          {
            id: 'faq-withdraw',
            question: 'Puis-je retirer à tout moment ?',
            answerMarkdown:
              'L\'épargne flexible et les cryptos peuvent être retirées sous 24 h. Les parts immobilières peuvent être revendues sur notre marché secondaire interne, sous réserve de liquidité.',
          },
        ],
      },
    },
    {
      key: 'cta',
      order: 10,
      data: {
        title: 'Le patrimoine\ncommence <em>aujourd\'hui.</em>',
        description:
          'Téléchargez l\'application Vancelian. Inscription en quelques minutes, premier investissement à partir de 100 €.',
        primaryButtonText: 'Télécharger l\'app',
        primaryButtonHref: '#download-app',
        showPrimaryButton: true,
        showSecondaryButton: false,
        backgroundColor: '#141208',
      },
    },
  ]
}

async function main() {
  if (!fs.existsSync(ZIP_ROOT)) {
    throw new Error(
      `Répertoire ZIP introuvable (${ZIP_ROOT}). Extrayez home.zip dans /tmp/home-zip/export-home ou définissez VANCELIAN_HOME_ZIP_ROOT.`,
    )
  }

  console.log('Médias Vancelian…')
  const media = await seedMedia()

  const page = await prisma.page.upsert({
    where: { slug: PAGE_SLUG },
    update: {
      urlPath: '/',
      title: 'Vancelian — Bâtir son patrimoine',
      description: 'Immobilier premium tokenisé, épargne flexible, cryptomonnaies.',
      themeColor: 'light',
      template: 'homepage',
    },
    create: {
      slug: PAGE_SLUG,
      urlPath: '/',
      title: 'Vancelian — Bâtir son patrimoine',
      description: 'Immobilier premium tokenisé, épargne flexible, cryptomonnaies.',
      themeColor: 'light',
      template: 'homepage',
    },
  })

  const sections = buildSections(media)
  const keepKeys = new Set(sections.map((s) => s.key))

  const existing = await prisma.section.findMany({ where: { pageId: page.id } })
  for (const s of existing) {
    if (!keepKeys.has(s.key)) {
      await prisma.sectionContent.deleteMany({ where: { sectionId: s.id } })
      await prisma.section.delete({ where: { id: s.id } })
      console.log(`  removed legacy section ${s.key}`)
    }
  }

  for (const def of sections) {
    const section = await prisma.section.upsert({
      where: { pageId_key: { pageId: page.id, key: def.key } },
      update: { order: def.order, schemaVersion: 'v1' },
      create: {
        pageId: page.id,
        key: def.key,
        order: def.order,
        schemaVersion: 'v1',
      },
    })

    await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: section.id,
          locale: 'fr',
          status: ContentStatus.PUBLISHED,
        },
      },
      update: { data: def.data as Prisma.InputJsonValue },
      create: {
        sectionId: section.id,
        locale: 'fr',
        status: ContentStatus.PUBLISHED,
        data: def.data as Prisma.InputJsonValue,
      },
    })

    console.log(`  section ${def.order} ${def.key}`)
  }

  console.log('Done. Homepage Vancelian CMS seedée (slug=home).')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
