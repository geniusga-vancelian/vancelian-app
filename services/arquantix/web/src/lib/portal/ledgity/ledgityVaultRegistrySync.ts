import type { PortalMorphoVaultConfig } from '@prisma/client'

import {
  LEDGITY_CHAIN_ID,
  LEDGITY_EURC_ADDRESS,
  LEDGITY_LYEURC_VAULT,
  LEDGITY_LYUSDC_VAULT,
  LEDGITY_USDC_ADDRESS,
  normalizeVaultAddress,
} from '@/lib/portal/ledgity/ledgityConstants'
import { prisma } from '@/lib/prisma'

const VAULT_ASSETS: Record<string, { address: string; symbol: string; decimals: number }> = {
  [normalizeVaultAddress(LEDGITY_LYUSDC_VAULT)]: {
    address: LEDGITY_USDC_ADDRESS,
    symbol: 'USDC',
    decimals: 6,
  },
  [normalizeVaultAddress(LEDGITY_LYEURC_VAULT)]: {
    address: LEDGITY_EURC_ADDRESS,
    symbol: 'EURC',
    decimals: 6,
  },
}

export async function upsertLedgityVaultRegistryRow(config: PortalMorphoVaultConfig): Promise<void> {
  const vaultAddress = normalizeVaultAddress(config.vaultAddress)
  const asset = VAULT_ASSETS[vaultAddress] ?? {
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
