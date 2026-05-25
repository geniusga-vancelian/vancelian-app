/**
 * Export / import `portal_morpho_vault_configs` (upsert par vault_address).
 *
 * Usage :
 *   npx tsx scripts/sync-morpho-vault-configs.ts export > morpho-vault-configs.json
 *   npx tsx scripts/sync-morpho-vault-configs.ts import morpho-vault-configs.json
 *   npx tsx scripts/sync-morpho-vault-configs.ts import --stdin < morpho-vault-configs.json
 */
import { readFileSync } from 'node:fs'

import { PrismaClient, type PortalMorphoIntegrationMode } from '@prisma/client'
import { randomUUID } from 'node:crypto'

import { normalizeVaultAddress } from '../src/lib/portal/morphoConstants'

type VaultConfigExport = {
  vaultAddress: string
  chainId?: number
  integrationMode: PortalMorphoIntegrationMode
  privyVaultId?: string | null
  label?: string | null
  description?: string | null
  curator?: string | null
  sortOrder?: number
  isPublished?: boolean
}

const prisma = new PrismaClient()

function parseArgs(): { mode: 'export' | 'import'; file?: string; stdin: boolean } {
  const [, , mode, file] = process.argv
  if (mode === 'export') return { mode: 'export', stdin: false }
  if (mode === 'import') {
    if (file === '--stdin') return { mode: 'import', stdin: true }
    if (!file) throw new Error('Usage: import <file.json> | import --stdin')
    return { mode: 'import', file, stdin: false }
  }
  throw new Error('Usage: export | import <file.json> | import --stdin')
}

async function exportConfigs(): Promise<void> {
  const rows = await prisma.portalMorphoVaultConfig.findMany({
    orderBy: [{ sortOrder: 'asc' }, { createdAt: 'asc' }],
  })
  const payload: VaultConfigExport[] = rows.map((row) => ({
    vaultAddress: row.vaultAddress,
    chainId: row.chainId,
    integrationMode: row.integrationMode,
    privyVaultId: row.privyVaultId,
    label: row.label,
    description: row.description,
    curator: row.curator,
    sortOrder: row.sortOrder,
    isPublished: row.isPublished,
  }))
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`)
}

async function importConfigs(raw: string): Promise<void> {
  const items = JSON.parse(raw) as VaultConfigExport[]
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
  console.log(`[morpho:sync-vault-configs] upserted=${upserted}`)
}

async function main() {
  const args = parseArgs()
  if (args.mode === 'export') {
    await exportConfigs()
    return
  }
  const raw = args.stdin ? readFileSync(0, 'utf8') : readFileSync(args.file!, 'utf8')
  await importConfigs(raw)
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
