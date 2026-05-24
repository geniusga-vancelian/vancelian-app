import type { PortalMorphoVaultConfig } from '@prisma/client'

import {
  getPortalEarnVaultConfigs,
  type PortalEarnVaultConfig,
} from '@/lib/portal/privyEarnConfig'
import {
  MORPHO_DEFAULT_PRIVY_VAULT_ID,
  MORPHO_DEFAULT_VAULT_ADDRESS,
  normalizeVaultAddress,
} from '@/lib/portal/morphoConstants'
import { prisma } from '@/lib/prisma'

export async function listPortalMorphoVaultConfigs(): Promise<PortalMorphoVaultConfig[]> {
  return prisma.portalMorphoVaultConfig.findMany({
    orderBy: [{ sortOrder: 'asc' }, { createdAt: 'asc' }],
  })
}

export async function listPublishedPortalMorphoVaultConfigs(): Promise<PortalMorphoVaultConfig[]> {
  return prisma.portalMorphoVaultConfig.findMany({
    where: { isPublished: true },
    orderBy: [{ sortOrder: 'asc' }, { createdAt: 'asc' }],
  })
}

/** Fallback env-only quand la table est vide (dev). */
export function getEnvFallbackMorphoVaultConfigs(): PortalMorphoVaultConfig[] {
  const earnConfigs = getPortalEarnVaultConfigs()
  const now = new Date()
  return earnConfigs.map((config, index) => ({
    id: `env-${config.vaultId}`,
    vaultAddress:
      config.vaultId === MORPHO_DEFAULT_PRIVY_VAULT_ID
        ? normalizeVaultAddress(MORPHO_DEFAULT_VAULT_ADDRESS)
        : '',
    chainId: 8453,
    integrationMode: 'privy_earn',
    privyVaultId: config.vaultId,
    label: config.label ?? null,
    description: config.description ?? null,
    curator: null,
    sortOrder: index,
    isPublished: true,
    createdAt: now,
    updatedAt: now,
  }))
}

export async function resolvePortalMorphoVaultConfigs(options?: {
  publishedOnly?: boolean
}): Promise<PortalMorphoVaultConfig[]> {
  const rows = options?.publishedOnly
    ? await listPublishedPortalMorphoVaultConfigs()
    : await listPortalMorphoVaultConfigs()
  if (rows.length) return rows
  return getEnvFallbackMorphoVaultConfigs()
}

export function findEarnConfigForMorphoRow(
  row: PortalMorphoVaultConfig,
  earnConfigs: PortalEarnVaultConfig[],
): PortalEarnVaultConfig | undefined {
  if (row.integrationMode !== 'privy_earn' || !row.privyVaultId) return undefined
  return earnConfigs.find((config) => config.vaultId === row.privyVaultId)
}
