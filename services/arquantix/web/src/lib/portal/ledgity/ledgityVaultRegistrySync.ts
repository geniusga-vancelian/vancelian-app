import type { PortalMorphoVaultConfig } from '@prisma/client'

import {
  LEDGITY_CHAIN_ID,
  normalizeVaultAddress,
  resolveKnownLedgityVaultAsset,
} from '@/lib/portal/ledgity/ledgityConstants'
import { prisma } from '@/lib/prisma'

export async function upsertLedgityVaultRegistryRow(config: PortalMorphoVaultConfig): Promise<void> {
  const vaultAddress = normalizeVaultAddress(config.vaultAddress)
  const asset = resolveKnownLedgityVaultAsset(vaultAddress) ?? {
    address: 'unknown',
    symbol: 'USDC',
    decimals: 6,
  }

  await prisma.defiVaultRegistry.upsert({
    where: {
      chainId_vaultAddress: {
        chainId: config.chainId ?? LEDGITY_CHAIN_ID,
        vaultAddress,
      },
    },
    create: {
      chainId: config.chainId ?? LEDGITY_CHAIN_ID,
      vaultAddress,
      morphoVersion: 'ledgity',
      assetAddress: asset.address,
      assetSymbol: asset.symbol,
      assetDecimals: asset.decimals,
      name: config.label ?? null,
      curator: config.curator ?? 'Ledgity',
      integrationMode: config.integrationMode,
      privyVaultId: config.privyVaultId,
      portalConfigId: config.id,
      isActive: config.isPublished,
      lastSyncedAt: new Date(),
    },
    update: {
      morphoVersion: 'ledgity',
      assetAddress: asset.address,
      assetSymbol: asset.symbol,
      assetDecimals: asset.decimals,
      name: config.label ?? null,
      curator: config.curator ?? 'Ledgity',
      integrationMode: config.integrationMode,
      privyVaultId: config.privyVaultId,
      portalConfigId: config.id,
      isActive: config.isPublished,
      lastSyncedAt: new Date(),
    },
  })
}

export async function syncLedgityVaultRegistryFromConfigs(): Promise<{
  upserted: number
  syncedAt: string
}> {
  const configs = await prisma.portalMorphoVaultConfig.findMany({
    where: { integrationMode: 'ledgity_vault' },
    orderBy: [{ sortOrder: 'asc' }, { createdAt: 'asc' }],
  })

  for (const config of configs) {
    await upsertLedgityVaultRegistryRow(config)
  }

  return {
    upserted: configs.length,
    syncedAt: new Date().toISOString(),
  }
}
