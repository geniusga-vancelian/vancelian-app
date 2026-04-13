/**
 * Upsert idempotent d’un projet « Exclusive Offer » (table projects + project_i18n).
 *
 * Usage (depuis services/arquantix/web, avec DATABASE_URL chargé) :
 *   npx tsx scripts/seed-exclusive-offer-project.ts
 *
 * Ne crée pas de médias (cover / hero / galerie) : à ajouter via l’admin ou scripts dédiés R2.
 * Ne crée pas de lending_pool_product : liaison manuelle ou API Python après validation des montants.
 */

import { PrismaClient } from '@prisma/client'

import {
  EXCLUSIVE_OFFER_IMPORT_SLUG,
  getExclusiveOfferProjectTemplate,
} from '../prisma/data/exclusive-offer-project-template'

const prisma = new PrismaClient()

async function main() {
  const t = getExclusiveOfferProjectTemplate()
  const { i18n, ...projectFields } = t

  const project = await prisma.project.upsert({
    where: { slug: EXCLUSIVE_OFFER_IMPORT_SLUG },
    update: {
      status: projectFields.status,
      investmentCategory: projectFields.investmentCategory,
      youtubeUrl: projectFields.youtubeUrl,
    },
    create: {
      slug: projectFields.slug,
      status: projectFields.status,
      investmentCategory: projectFields.investmentCategory,
      youtubeUrl: projectFields.youtubeUrl,
    },
  })

  await prisma.projectI18n.upsert({
    where: {
      projectId_locale: {
        projectId: project.id,
        locale: i18n.locale,
      },
    },
    update: {
      title: i18n.title,
      location: i18n.location,
      shortDescription: i18n.shortDescription,
      description: i18n.description,
      metaTitle: i18n.metaTitle,
      metaDescription: i18n.metaDescription,
      descriptionLinks: i18n.descriptionLinks,
      howItWorks: i18n.howItWorks,
      keyInformation: i18n.keyInformation,
      competitiveAdvantages: i18n.competitiveAdvantages,
      faq: i18n.faq,
    },
    create: {
      projectId: project.id,
      locale: i18n.locale,
      title: i18n.title,
      location: i18n.location,
      shortDescription: i18n.shortDescription,
      description: i18n.description,
      metaTitle: i18n.metaTitle,
      metaDescription: i18n.metaDescription,
      descriptionLinks: i18n.descriptionLinks,
      howItWorks: i18n.howItWorks,
      keyInformation: i18n.keyInformation,
      competitiveAdvantages: i18n.competitiveAdvantages,
      faq: i18n.faq,
    },
  })

  console.log(
    JSON.stringify(
      {
        ok: true,
        slug: project.slug,
        id: project.id,
        status: project.status,
        message:
          'Projet upserté. Vérifier le rendu via GET /api/projects?locale=fr et l’admin /admin/projects.',
      },
      null,
      2
    )
  )
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
