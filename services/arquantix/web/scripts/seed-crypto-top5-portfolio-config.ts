/**
 * Prisma — config d’affichage Vault / Flutter pour CRYPTO_BUNDLE_TOP5.
 *
 * À exécuter après bootstrap_crypto_bundle_top5.py (produit présent dans le catalogue FastAPI).
 *
 * Usage (services/arquantix/web) :
 *   npx tsx scripts/seed-crypto-top5-portfolio-config.ts
 */

import { randomUUID } from 'crypto'

import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const PRODUCT_CODE = 'CRYPTO_BUNDLE_TOP5'

async function main() {
  const greys = ['#374151', '#6B7280', '#9CA3AF', '#D1D5DB', '#E5E7EB']
  const slices = [
    { label: 'BTC', percentage: 50, colorHex: '#F7931A' },
    { label: 'ETH', percentage: 20, colorHex: '#627EEA' },
    { label: 'SOL', percentage: 10, colorHex: '#9945FF' },
    { label: 'XRP', percentage: 10, colorHex: '#23292F' },
    { label: 'BNB', percentage: 10, colorHex: '#F3BA2F' },
  ].map((s, i) => ({
    ...s,
    colorHex: s.colorHex || greys[i % greys.length],
  }))

  const modules = [
    {
      id: randomUUID(),
      type: 'TitlePage',
      enabled: true,
      content: {
        title: 'Top 5 Crypto Bundle',
        subtitle:
          'Diversification sur cinq crypto-actifs majeurs. Souscription en USDC ; allocation cible ci-dessous.',
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
        title: 'Allocation cible',
        introText:
          'Les pourcentages représentent la répartition cible des actifs sous-jacents. L’USDC est uniquement la devise d’entrée pour souscrire, pas un composant du panier.',
        size: 'large',
        slices,
      },
    },
  ]

  const row = await prisma.portfolioProductConfig.upsert({
    where: { productCode: PRODUCT_CODE },
    update: {
      modules: modules as object[],
      sortOrder: 15,
      isPublished: true,
    },
    create: {
      productCode: PRODUCT_CODE,
      modules: modules as object[],
      sortOrder: 15,
      isPublished: true,
    },
  })

  console.log(
    JSON.stringify(
      {
        ok: true,
        productCode: row.productCode,
        id: row.id,
        sortOrder: row.sortOrder,
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
