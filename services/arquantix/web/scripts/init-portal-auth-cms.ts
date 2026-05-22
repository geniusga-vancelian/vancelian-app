/**
 * Initialise le module Portail Auth CMS + pages légales (Terms, Privacy).
 * Run: npx tsx scripts/init-portal-auth-cms.ts
 */

import { ContentStatus, PrismaClient } from '@prisma/client'
import { getDefaultPortalAuthContent } from '../src/lib/cms/portal-auth'
import { portalAuthJsonV2Schema } from '../src/lib/cms/portalAuthSchema'

const prisma = new PrismaClient()

type LegalPageDef = {
  slug: string
  title: string
  urlPath: string
  sectionTitle: string
  body: string
}

const LEGAL_PAGES: LegalPageDef[] = [
  {
    slug: 'terms',
    title: 'Terms of Service',
    urlPath: '/en/terms',
    sectionTitle: 'Terms of Service',
    body: `These Terms of Service govern your access to and use of the Vancelian platform.

Please replace this placeholder content with your legal text via **Admin → Pages → terms**.`,
  },
  {
    slug: 'privacy-policy',
    title: 'Privacy Policy',
    urlPath: '/en/privacy-policy',
    sectionTitle: 'Privacy Policy',
    body: `This Privacy Policy describes how Vancelian collects, uses, and protects your personal data.

Please replace this placeholder content with your legal text via **Admin → Pages → privacy-policy**.`,
  },
]

async function upsertLegalPage(def: LegalPageDef) {
  const page = await prisma.page.upsert({
    where: { slug: def.slug },
    update: {
      title: def.title,
      urlPath: def.urlPath,
      template: 'default',
      isSystemPage: true,
      showInNav: false,
    },
    create: {
      slug: def.slug,
      title: def.title,
      urlPath: def.urlPath,
      template: 'default',
      isSystemPage: true,
      showInNav: false,
    },
  })

  const section = await prisma.section.upsert({
    where: { pageId_key: { pageId: page.id, key: 'media_text' } },
    update: { order: 0, schemaVersion: 'v1' },
    create: {
      pageId: page.id,
      key: 'media_text',
      order: 0,
      schemaVersion: 'v1',
    },
  })

  const data = {
    title: def.sectionTitle,
    description: def.body,
    eyebrow: '',
    mediaRight: false,
  }

  for (const status of [ContentStatus.DRAFT, ContentStatus.PUBLISHED] as const) {
    for (const locale of ['en', 'fr', 'it'] as const) {
      await prisma.sectionContent.upsert({
        where: {
          sectionId_locale_status: {
            sectionId: section.id,
            locale,
            status,
          },
        },
        update: { data },
        create: {
          sectionId: section.id,
          locale,
          status,
          data,
        },
      })
    }
  }

  await prisma.pageI18n.upsert({
    where: { pageId_locale: { pageId: page.id, locale: 'en' } },
    update: { title: def.title, description: def.sectionTitle },
    create: {
      pageId: page.id,
      locale: 'en',
      title: def.title,
      description: def.sectionTitle,
    },
  })

  console.log(`  ✅ Page légale « ${def.slug} » → ${def.urlPath}`)
  return page
}

async function seedPortalAuthJson() {
  const defaults = getDefaultPortalAuthContent()
  const enBlock = {
    shell: {
      backToWebsiteLabel: defaults.shell.backToWebsiteLabel,
      backToWebsiteHref: defaults.shell.backToWebsiteHref,
    },
    login: defaults.login,
    signup: defaults.signup,
    verify: defaults.verify,
    legal: defaults.legal,
  }

  const doc = portalAuthJsonV2Schema.parse({
    version: 2,
    defaultLocale: 'en',
    resendSeconds: defaults.resendSeconds,
    ssoEnabled: defaults.ssoEnabled,
    locales: {
      en: enBlock,
      fr: {},
      it: {},
    },
  })

  const existing = await prisma.globalSettings.findFirst()
  if (existing) {
    await prisma.globalSettings.update({
      where: { id: existing.id },
      data: { portalAuthJson: doc as object },
    })
  } else {
    await prisma.globalSettings.create({
      data: { portalAuthJson: doc as object },
    })
  }

  console.log('  ✅ portal_auth_json initialisé (EN + defaults légaux)')
}

async function main() {
  console.log('🌱 Initialisation Portail Auth CMS…')
  for (const def of LEGAL_PAGES) {
    await upsertLegalPage(def)
  }
  await seedPortalAuthJson()
  console.log('')
  console.log('Prochaines étapes :')
  console.log('1. Admin → Structure du site → Portail Auth')
  console.log('2. Admin → Pages → terms / privacy-policy (contenu légal)')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
