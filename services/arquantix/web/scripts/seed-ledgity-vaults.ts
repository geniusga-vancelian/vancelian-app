/**
 * Seed vault configs ERC-4626 publiés sur Base :
 * - Vancelian/Arquantix : vfEUR, axUSD, axDUBAI, axBALI (mainnet CDC v0.3)
 * - Ledgity natifs : lyUSDC, lyEURC
 *
 * Usage :
 *   npm run ledgity:seed-vaults
 */
import { readFileSync } from 'node:fs'
import { randomUUID } from 'node:crypto'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { PrismaClient } from '@prisma/client'

import { normalizeVaultAddress } from '../src/lib/portal/ledgity/ledgityConstants'
import { syncLedgityVaultRegistryFromConfigs } from '../src/lib/portal/ledgity/ledgityVaultRegistrySync'

const prisma = new PrismaClient()

const __dirname = dirname(fileURLToPath(import.meta.url))
const SEED_PATH = join(__dirname, 'data/ledgity-vault-configs.seed.json')

type VaultConfigSeed = {
  vaultAddress: string
  chainId?: number
  integrationMode: 'ledgity_vault'
  privyVaultId?: string | null
  label?: string | null
  description?: string | null
  curator?: string | null
  sortOrder?: number
  isPublished?: boolean
}

async function main() {
  const raw = readFileSync(SEED_PATH, 'utf8')
  const items = JSON.parse(raw) as VaultConfigSeed[]
  if (!Array.isArray(items)) throw new Error('JSON array expected')

  let upserted = 0
  for (const item of items) {
    const vaultAddress = normalizeVaultAddress(item.vaultAddress)
    await prisma.portalMorphoVaultConfig.upsert({
      where: { vaultAddress },
      create: {
        id: randomUUID(),
        vaultAddress,
        chainId: item.chainId ?? 8453,
        integrationMode: item.integrationMode,
        privyVaultId: item.privyVaultId ?? null,
        label: item.label ?? null,
        description: item.description ?? null,
        curator: item.curator ?? null,
        sortOrder: item.sortOrder ?? 999,
        isPublished: item.isPublished ?? false,
      },
      update: {
        chainId: item.chainId ?? 8453,
        integrationMode: item.integrationMode,
        privyVaultId: item.privyVaultId ?? null,
        label: item.label ?? null,
        description: item.description ?? null,
        curator: item.curator ?? null,
        sortOrder: item.sortOrder ?? 999,
        isPublished: item.isPublished ?? false,
      },
    })
    upserted += 1
  }

  const registry = await syncLedgityVaultRegistryFromConfigs()

  console.log(`[ledgity:seed-vaults] upserted=${upserted} registry=${registry.upserted}`)
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
