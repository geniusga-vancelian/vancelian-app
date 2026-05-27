/**
 * Prisma — CMS config for CRYPTO_BUNDLE_TWO_KINGS and CRYPTO_BUNDLE_CRYPTO_MAJORS.
 *
 * Run after:
 *   cd ../api && python3 scripts/bootstrap_crypto_bundle_base_portfolio.py
 *
 * Usage (services/arquantix/web):
 *   npx tsx scripts/seed-crypto-base-bundles-portfolio-config.ts
 */

import { randomUUID } from 'crypto'

import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const LEGACY_PRODUCT_CODES = [
  'TOP_5',
  'TOP_2',
  'CRYPTO_BUNDLE_TOP5',
  'CRYPTO_BUNDLE_TOP_5',
  'CRYPTO_BUNDLE_TOP2',
  'CRYPTO_BUNDLE_TOP_2',
] as const

type BundleUiSpec = {
  productCode: string
  sortOrder: number
  title: string
  subtitle: string
  mediaKey: string
  imageUrl: string
  slices: { label: string; percentage: number; colorHex: string }[]
}

const BUNDLES: BundleUiSpec[] = [
  {
    productCode: 'CRYPTO_BUNDLE_TWO_KINGS',
    sortOrder: 10,
    title: 'Two Crypto Kings',
    subtitle:
      'A concentrated allocation to Bitcoin (70%) and Ethereum (30%) on Base. cbBTC and cbETH are used for on-chain exposure.',
    mediaKey: 'bundle-two-crypto-kings-placeholder',
    imageUrl: 'https://picsum.photos/seed/vancelian-two-crypto-kings/1200/800',
    slices: [
      { label: 'Bitcoin', percentage: 70, colorHex: '#F7931A' },
      { label: 'Ethereum', percentage: 30, colorHex: '#627EEA' },
    ],
  },
  {
    productCode: 'CRYPTO_BUNDLE_CRYPTO_MAJORS',
    sortOrder: 20,
    title: 'Crypto Majors',
    subtitle:
      'Bitcoin, Ethereum, and three DeFi leaders (Chainlink, Aave, Uniswap). 50% / 30% core (cbBTC / cbETH) plus ~6.7% each on the remaining assets.',
    mediaKey: 'bundle-crypto-majors-placeholder',
    imageUrl: 'https://picsum.photos/seed/vancelian-crypto-majors/1200/800',
    slices: [
      { label: 'Bitcoin', percentage: 50, colorHex: '#F7931A' },
      { label: 'Ethereum', percentage: 30, colorHex: '#627EEA' },
      { label: 'Chainlink', percentage: 6.7, colorHex: '#2A5ADA' },
      { label: 'Aave', percentage: 6.7, colorHex: '#B6509E' },
      { label: 'Uniswap', percentage: 6.6, colorHex: '#FF007A' },
    ],
  },
]

async function upsertPlaceholderMedia(spec: BundleUiSpec) {
  return prisma.media.upsert({
    where: { key: spec.mediaKey },
    update: {
      url: spec.imageUrl,
      filename: `${spec.mediaKey}.jpg`,
      mimeType: 'image/jpeg',
      size: 0,
      alt: `${spec.title} (placeholder)`,
    },
    create: {
      key: spec.mediaKey,
      url: spec.imageUrl,
      filename: `${spec.mediaKey}.jpg`,
      mimeType: 'image/jpeg',
      size: 0,
      alt: `${spec.title} (placeholder)`,
    },
  })
}

function buildModules(spec: BundleUiSpec) {
  return [
    {
      id: randomUUID(),
      type: 'TitlePage',
      enabled: true,
      content: {
        title: spec.title,
        subtitle: spec.subtitle,
      },
    },
    {
      id: randomUUID(),
      type: 'PerformanceChart',
      enabled: true,
      content: { title: 'Performance' },
    },
    {
      id: randomUUID(),
      type: 'AllocationModule',
      enabled: true,
      content: {
        title: 'Target allocation',
        introText:
          'Percentages reflect the target weight of each underlying asset. USDC is the entry currency only and is not part of the basket.',
        size: 'large',
        slices: spec.slices,
      },
    },
  ]
}

async function upsertBundleConfig(spec: BundleUiSpec) {
  const media = await upsertPlaceholderMedia(spec)
  const modules = buildModules(spec)

  const row = await prisma.portfolioProductConfig.upsert({
    where: { productCode: spec.productCode },
    update: {
      modules: modules as object[],
      headerMediaId: media.id,
      detailMediaId: media.id,
      sortOrder: spec.sortOrder,
      isPublished: true,
    },
    create: {
      productCode: spec.productCode,
      modules: modules as object[],
      headerMediaId: media.id,
      detailMediaId: media.id,
      sortOrder: spec.sortOrder,
      isPublished: true,
    },
  })

  return { row, mediaId: media.id }
}

async function deleteLegacyConfigs() {
  const result = await prisma.portfolioProductConfig.deleteMany({
    where: { productCode: { in: [...LEGACY_PRODUCT_CODES] } },
  })
  if (result.count > 0) {
    console.log(`  ✓ Deleted ${result.count} legacy CMS config row(s)`)
  }
}

async function main() {
  const results = []
  for (const spec of BUNDLES) {
    const { row, mediaId } = await upsertBundleConfig(spec)
    results.push({
      productCode: row.productCode,
      id: row.id,
      sortOrder: row.sortOrder,
      mediaId,
    })
  }

  await deleteLegacyConfigs()

  console.log(JSON.stringify({ ok: true, bundles: results }, null, 2))
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
