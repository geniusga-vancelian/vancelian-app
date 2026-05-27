/**
 * Remove legacy bundle CMS rows (TOP_5, CRYPTO_BUNDLE_TOP5, TOP2, …).
 *
 * Usage:
 *   npx tsx scripts/delete-legacy-crypto-bundle-configs.ts
 */

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

async function main() {
  const result = await prisma.portfolioProductConfig.deleteMany({
    where: { productCode: { in: [...LEGACY_PRODUCT_CODES] } },
  })
  const remaining = await prisma.portfolioProductConfig.findMany({
    select: { productCode: true, isPublished: true },
    orderBy: { sortOrder: 'asc' },
  })
  console.log(
    JSON.stringify(
      { ok: true, deletedCount: result.count, remaining },
      null,
      2,
    ),
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
