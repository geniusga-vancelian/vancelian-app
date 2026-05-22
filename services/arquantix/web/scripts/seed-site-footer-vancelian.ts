/**
 * Configure le footer global Vancelian via CMS (`global_settings.footer_json`).
 * Contenu aligné sur Home.html du pack DS.
 *
 * Usage :
 *   cd services/arquantix/web && npx tsx scripts/seed-site-footer-vancelian.ts
 */

import fs from 'node:fs'
import path from 'node:path'
import { PrismaClient, Prisma } from '@prisma/client'
import type { FooterJsonInput, FooterJsonV2 } from '@/lib/sections/library'

const prisma = new PrismaClient()

const LOGO_KEY = 'brand/vancelian/logo-black-h.svg'
const LOGO_URL = '/brand/vancelian/logo-black-h.svg'
const LOGO_FILE = path.join(process.cwd(), 'public/brand/vancelian/logo-black-h.svg')
const ZIP_LOGO_FILE = path.join(
  process.env.VANCELIAN_HOME_ZIP_ROOT || '/tmp/home-zip/export-home',
  'assets/logos/logo-black-h.svg',
)

const FOOTER_FR: FooterJsonInput = {
  logoMediaInvert: true,
  backgroundColor: '#141208',
  newsletterVisible: false,
  description: 'Bâtir son patrimoine, aujourd’hui.',
  companyAddress:
    'Vancelian SAS · Sophia Antipolis\nCapital social : XX XXX €\nRCS Antibes : XXX XXX XXX\nEnregistrement PSAN : E2024-XXX',
  copyright: '© 2026 Vancelian SAS. Tous droits réservés.',
  secondaryNote: 'Made in Sophia Antipolis · Site fait avec attention',
  legalTexts: [
    'Investir comporte des risques de perte en capital. Les performances passées ne préjugent pas des performances futures. Vancelian est enregistré comme prestataire de services sur actifs numériques (PSAN) auprès de l’Autorité des marchés financiers (AMF) sous le numéro E2024-XXX. Avant tout investissement, consultez attentivement les conditions générales et le document d’information clé pour l’investisseur.',
  ],
  socialLinks: [
    { platform: 'linkedin', href: 'https://www.linkedin.com/company/vancelian' },
    { platform: 'x', href: 'https://x.com/vancelian' },
    { platform: 'instagram', href: 'https://www.instagram.com/vancelian' },
  ],
  links: [
    { label: 'Épargne flexible', href: '/fr/epargne', category: 'Produit' },
    { label: 'Offres exclusives', href: '/fr/offres-exclusives', category: 'Produit' },
    { label: 'Cryptomonnaies', href: '/fr/crypto', category: 'Produit' },
    { label: 'Carte Visa', href: '/fr/carte', category: 'Produit' },
    { label: 'Vancelian Pro', href: '/fr/pro', category: 'Produit' },
    { label: 'À propos', href: '/fr/a-propos', category: 'Société' },
    { label: 'Carrières', href: '/fr/carrieres', category: 'Société' },
    { label: 'Presse', href: '/fr/presse', category: 'Société' },
    { label: 'Blog', href: '/fr/blog', category: 'Société' },
    { label: 'Conditions générales', href: '/fr/cgu', category: 'Légal' },
    { label: 'Politique de confidentialité', href: '/fr/confidentialite', category: 'Légal' },
    { label: 'Mentions légales', href: '/fr/mentions-legales', category: 'Légal' },
    { label: 'Cookies', href: '/fr/cookies', category: 'Légal' },
    { label: 'Centre d’aide', href: '/fr/aide', category: 'Support' },
    { label: 'Contact', href: '/fr/contact', category: 'Support' },
    { label: 'Statut des services', href: '/fr/statut', category: 'Support' },
    { label: 'Lexique', href: '/fr/lexique', category: 'Support' },
  ],
}

const FOOTER_EN: FooterJsonInput = {
  ...FOOTER_FR,
  description: 'Build your wealth, today.',
  companyAddress:
    'Vancelian SAS · Sophia Antipolis\nShare capital: XX XXX €\nRCS Antibes: XXX XXX XXX\nPSAN registration: E2024-XXX',
  copyright: '© 2026 Vancelian SAS. All rights reserved.',
  secondaryNote: 'Made in Sophia Antipolis · Crafted with care',
  legalTexts: [
    'Investing involves the risk of capital loss. Past performance is not indicative of future results. Vancelian is registered as a Digital Asset Service Provider (PSAN) with the AMF under number E2024-XXX. Before investing, please read the terms and conditions and the key information document carefully.',
  ],
  links: FOOTER_FR.links?.map((l) => ({
    ...l,
    href: l.href.replace(/^\/fr\//, '/en/'),
    category:
      l.category === 'Produit'
        ? 'Product'
        : l.category === 'Société'
          ? 'Company'
          : l.category === 'Légal'
            ? 'Legal'
            : 'Support',
    label:
      l.label === 'Épargne flexible'
        ? 'Flexible savings'
        : l.label === 'Offres exclusives'
          ? 'Exclusive offers'
          : l.label === 'Cryptomonnaies'
            ? 'Cryptocurrencies'
            : l.label === 'Carte Visa'
              ? 'Visa card'
              : l.label === 'À propos'
                ? 'About'
                : l.label === 'Carrières'
                  ? 'Careers'
                  : l.label === 'Presse'
                    ? 'Press'
                    : l.label === 'Conditions générales'
                      ? 'Terms & conditions'
                      : l.label === 'Politique de confidentialité'
                        ? 'Privacy policy'
                        : l.label === 'Mentions légales'
                          ? 'Legal notice'
                          : l.label === 'Centre d’aide'
                            ? 'Help center'
                            : l.label === 'Statut des services'
                              ? 'Service status'
                              : l.label === 'Lexique'
                                ? 'Glossary'
                                : l.label,
  })),
}

async function ensureNavbarLogoMedia() {
  if (!fs.existsSync(LOGO_FILE) && fs.existsSync(ZIP_LOGO_FILE)) {
    fs.mkdirSync(path.dirname(LOGO_FILE), { recursive: true })
    fs.copyFileSync(ZIP_LOGO_FILE, LOGO_FILE)
  }
  if (!fs.existsSync(LOGO_FILE)) {
    throw new Error(`Logo navbar introuvable : ${LOGO_FILE}`)
  }

  const stat = fs.statSync(LOGO_FILE)
  return prisma.media.upsert({
    where: { key: LOGO_KEY },
    update: {
      url: LOGO_URL,
      filename: 'logo-black-h.svg',
      mimeType: 'image/svg+xml',
      size: stat.size,
      alt: 'Vancelian',
    },
    create: {
      key: LOGO_KEY,
      url: LOGO_URL,
      filename: 'logo-black-h.svg',
      mimeType: 'image/svg+xml',
      size: stat.size,
      alt: 'Vancelian',
    },
  })
}

function buildFooterV2(logoMediaId: string): FooterJsonV2 {
  return {
    version: 2,
    defaultLocale: 'fr',
    locales: {
      fr: { ...FOOTER_FR, logoMediaId },
      en: { ...FOOTER_EN, logoMediaId },
    },
  }
}

async function main() {
  const logo = await ensureNavbarLogoMedia()
  console.log(`  logo navbar → media ${logo.id}`)

  const footerJson = buildFooterV2(logo.id)
  const existing = await prisma.globalSettings.findFirst()

  if (existing) {
    await prisma.globalSettings.update({
      where: { id: existing.id },
      data: { footerJson: footerJson as Prisma.InputJsonValue },
    })
    console.log(`  global_settings.footer_json mis à jour (id=${existing.id})`)
  } else {
    await prisma.globalSettings.create({
      data: { footerJson: footerJson as Prisma.InputJsonValue },
    })
    console.log('  global_settings créé')
  }

  console.log('Done. Footer CMS aligné sur Home.html.')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
