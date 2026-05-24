import type { PortalMorphoVaultConfig } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import { fetchMorphoVaultsByAddresses } from '@/lib/portal/morphoGraphql'
import { normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import { listPortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'

export type MorphoVaultRegistrySyncResult = {
  scanned: number
  upserted: number
  skipped: number
  errors: Array<{ vaultAddress: string; message: string }>
  syncedAt: string
}

async function upsertRegistryRow(args: {
  config: PortalMorphoVaultConfig
  gql?: Awaited<ReturnType<typeof fetchMorphoVaultsByAddresses>>[number]
}) {
  const vaultAddress = normalizeVaultAddress(args.config.vaultAddress)
  const asset = args.gql?.asset ?? { address: '', symbol: 'USDC', decimals: 6 }

  await prisma.defiVaultRegistry.upsert({
    where: {
      chainId_vaultAddress: {
        chainId: args.config.chainId,
        vaultAddress,
      },
    },
    create: {
      chainId: args.config.chainId,
      vaultAddress,
      morphoVersion: args.gql?.version ?? 'unknown',
      assetAddress: asset.address || 'unknown',
      assetSymbol: asset.symbol || 'USDC',
      assetDecimals: asset.decimals ?? 6,
      name: args.config.label ?? args.gql?.name ?? null,
      curator: args.config.curator ?? args.gql?.curator ?? null,
      integrationMode: args.config.integrationMode,
      privyVaultId: args.config.privyVaultId,
      portalConfigId: args.config.id,
      isActive: args.config.isPublished,
      lastSyncedAt: new Date(),
    },
    update: {
      morphoVersion: args.gql?.version ?? 'unknown',
      assetAddress: asset.address || 'unknown',
      assetSymbol: asset.symbol || 'USDC',
      assetDecimals: asset.decimals ?? 6,
      name: args.config.label ?? args.gql?.name ?? null,
      curator: args.config.curator ?? args.gql?.curator ?? null,
      integrationMode: args.config.integrationMode,
      privyVaultId: args.config.privyVaultId,
      portalConfigId: args.config.id,
      isActive: args.config.isPublished,
      lastSyncedAt: new Date(),
    },
  })
}

/** Alimente `defi_vault_registry` depuis PortalMorphoVaultConfig + Morpho GraphQL. */
export async function syncMorphoVaultRegistryFromConfigs(): Promise<MorphoVaultRegistrySyncResult> {
  const configs = await listPortalMorphoVaultConfigs()
  const addresses = configs
    .map((row) => row.vaultAddress?.trim())
    .filter((row): row is string => Boolean(row))

  const gqlRows = addresses.length
    ? await fetchMorphoVaultsByAddresses({ addresses })
    : []

  const gqlByAddress = new Map(
    gqlRows.map((row) => [normalizeVaultAddress(row.address), row]),
  )

  const result: MorphoVaultRegistrySyncResult = {
    scanned: configs.length,
    upserted: 0,
    skipped: 0,
    errors: [],
    syncedAt: new Date().toISOString(),
  }

  for (const config of configs) {
    if (!config.vaultAddress?.trim()) {
      result.skipped += 1
      continue
    }
    try {
      const gql = gqlByAddress.get(normalizeVaultAddress(config.vaultAddress))
      await upsertRegistryRow({ config, gql })
      result.upserted += 1
    } catch (error) {
      result.errors.push({
        vaultAddress: config.vaultAddress,
        message: error instanceof Error ? error.message : 'Erreur inconnue.',
      })
    }
  }

  return result
}
