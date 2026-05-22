/**
 * Insère le module FAQ sur la homepage Vancelian (après security, avant cta).
 *
 * Usage : npx tsx scripts/add-homepage-faq-section.ts
 */

import { PrismaClient, ContentStatus, Prisma } from '@prisma/client'

const prisma = new PrismaClient()
const PAGE_SLUG = 'home'
const FAQ_KEY = 'faq'
const INSERT_ORDER = 9

function faqItem(id: string, question: string, answerMarkdown: string) {
  return { id, question, answerMarkdown }
}

const FAQ_DATA_FR: Prisma.InputJsonObject = {
  eyebrow: 'QUESTIONS FRÉQUENTES',
  title: "L'essentiel\n<em>en bref.</em>",
  description: '',
  subtitle: '',
  support: {
    title: 'Une question ?',
    description: 'Notre équipe répond aux questions techniques sous 24 h.',
    ctaLabel: 'Contacter le support →',
    ctaHref: '/fr/contact',
    secondaryLinkLabel: 'FAQ complète →',
    secondaryLinkHref: '/fr/aide',
  },
  items: [
    faqItem(
      'faq-regulation',
      'Vancelian est-il régulé ?',
      'Oui. Vancelian est enregistré comme PSAN auprès de l\'AMF sous le numéro E2023-087. Nos opérations sont conformes au règlement européen MiCA.',
    ),
    faqItem(
      'faq-fees',
      'Quels sont les frais ?',
      'Aucun frais d\'abonnement. L\'immobilier tokenisé comporte 1 % de frais d\'entrée et 0,5 % de frais de gestion annuels. Les transactions crypto sont facturées à 1 %. Le détail est affiché dans l\'app avant chaque investissement.',
    ),
    faqItem(
      'faq-withdraw',
      'Puis-je retirer à tout moment ?',
      'L\'épargne flexible et les cryptos peuvent être retirées sous 24 h. Les parts immobilières peuvent être revendues sur notre marché secondaire interne, sous réserve de liquidité et de la période de blocage indiquée sur chaque offre.',
    ),
    faqItem(
      'faq-minimum',
      'Quel est le ticket minimum ?',
      'À partir de 100 € sur les offres immobilières exclusives. L\'épargne flexible accepte des dépôts dès 1 €. Les paniers crypto démarrent à 50 €.',
    ),
    faqItem(
      'faq-returns',
      'Comment sont versés les rendements ?',
      'Les revenus locatifs nets des biens tokenisés sont distribués trimestriellement, proportionnellement à vos parts, sur votre wallet Vancelian. Les intérêts d\'épargne sont crédités quotidiennement.',
    ),
    faqItem(
      'faq-tokenization',
      'Comment fonctionne la tokenisation ?',
      'Chaque actif est porté par un SPV dédié. Les parts sont émises en tokens ERC-1400, vous conférant des droits économiques proportionnels et un reporting transparent.',
    ),
  ],
}

const FAQ_DATA_EN: Prisma.InputJsonObject = {
  eyebrow: 'FREQUENTLY ASKED QUESTIONS',
  title: 'The essentials\n<em>in brief.</em>',
  description: '',
  subtitle: '',
  support: {
    title: 'Have a question?',
    description: 'Our team responds to technical questions within 24 hours.',
    ctaLabel: 'Contact support →',
    ctaHref: '/en/contact',
    secondaryLinkLabel: 'Full FAQ →',
    secondaryLinkHref: '/en/help',
  },
  items: [
    faqItem(
      'faq-regulation',
      'Is Vancelian regulated?',
      'Yes. Vancelian is registered as a Digital Asset Service Provider (DASP) with the AMF under registration number E2023-087. Our operations comply with the European MiCA framework.',
    ),
    faqItem(
      'faq-fees',
      'What are the fees?',
      'No subscription fees. Tokenized real estate carries a 1% entry fee and a 0.5% annual management fee. Crypto trades are charged at 1% per transaction. The full schedule is shown in-app before every investment.',
    ),
    faqItem(
      'faq-withdraw',
      'Can I withdraw at any time?',
      'Flexible savings and crypto holdings can be withdrawn within 24 hours. Real estate shares can be sold on our internal secondary market, subject to liquidity and any lock-up period stated on each offer.',
    ),
    faqItem(
      'faq-minimum',
      'What is the minimum investment?',
      'You can start from €100 on exclusive real estate offers. Flexible savings accepts deposits from €1. Crypto baskets require a minimum of €50.',
    ),
    faqItem(
      'faq-returns',
      'How are returns paid out?',
      'Net rental income from tokenized properties is distributed quarterly, proportional to your share, directly to your Vancelian wallet. Savings interest is credited daily.',
    ),
    faqItem(
      'faq-tokenization',
      'How does tokenization work?',
      'Each property is held by a dedicated SPV. Ownership shares are issued as ERC-1400 security tokens, giving you proportional economic rights and transparent on-chain reporting.',
    ),
  ],
}

async function upsertSectionContent(
  sectionId: string,
  locale: string,
  data: Prisma.InputJsonObject,
) {
  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId,
        locale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: { data },
    create: {
      sectionId,
      locale,
      status: ContentStatus.PUBLISHED,
      data,
    },
  })
}

async function main() {
  const page = await prisma.page.findUnique({
    where: { slug: PAGE_SLUG },
    include: {
      sections: { orderBy: { order: 'asc' } },
    },
  })

  if (!page) {
    throw new Error(`Page "${PAGE_SLUG}" introuvable`)
  }

  let faqSection = page.sections.find((s) => s.key === FAQ_KEY)

  if (!faqSection) {
    const toShift = page.sections.filter((s) => s.order >= INSERT_ORDER)
    for (const section of toShift.sort((a, b) => b.order - a.order)) {
      await prisma.section.update({
        where: { id: section.id },
        data: { order: section.order + 1 },
      })
      console.log(`  shifted ${section.key} → order ${section.order + 1}`)
    }

    faqSection = await prisma.section.create({
      data: {
        pageId: page.id,
        key: FAQ_KEY,
        order: INSERT_ORDER,
        schemaVersion: 'v1',
      },
    })
    console.log(`  created section ${FAQ_KEY} at order ${INSERT_ORDER}`)
  } else {
    console.log(`  section ${FAQ_KEY} already exists (order ${faqSection.order})`)
  }

  await upsertSectionContent(faqSection.id, 'fr', FAQ_DATA_FR)
  await upsertSectionContent(faqSection.id, 'en', FAQ_DATA_EN)
  console.log('  published FAQ content (fr + en)')

  console.log('Done. FAQ inserted after security, before cta.')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
