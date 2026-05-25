import type { PortalMorphoVaultConfig } from '@prisma/client'

import {
  MORPHO_DEFAULT_VAULT_ADDRESS,
  normalizeVaultAddress,
} from '@/lib/portal/morphoConstants'
import { prisma } from '@/lib/prisma'

const DIRECT_MORPHO_ONLY = 'direct_morpho'

function filterDirectMorphoConfigs(rows: PortalMorphoVaultConfig[]): PortalMorphoVaultConfig[] {
  return rows.filter((row) => row.integrationMode === DIRECT_MORPHO_ONLY)
}

export async function listPortalMorphoVaultConfigs(): Promise<PortalMorphoVaultConfig[]> {
  return filterDirectMorphoConfigs(
    await prisma.portalMorphoVaultConfig.findMany({
      orderBy: [{ sortOrder: 'asc' }, { createdAt: 'asc' }],
    }),
  )
}

export async function listPublishedPortalMorphoVaultConfigs(): Promise<PortalMorphoVaultConfig[]> {
  return filterDirectMorphoConfigs(
    await prisma.portalMorphoVaultConfig.findMany({
      where: { isPublished: true, integrationMode: DIRECT_MORPHO_ONLY },
      orderBy: [{ sortOrder: 'asc' }, { createdAt: 'asc' }],
    }),
  )
}

/** Fallback env-only quand la table est vide (dev). */
export function getEnvFallbackMorphoVaultConfigs(): PortalMorphoVaultConfig[] {
  const now = new Date()
  return [
    {
      id: 'env-direct-steakhouse',
      vaultAddress: normalizeVaultAddress(MORPHO_DEFAULT_VAULT_ADDRESS),
      chainId: 8453,
      integrationMode: DIRECT_MORPHO_ONLY,
      privyVaultId: null,
      label: 'Steakhouse Prime USDC',
      description: 'Vault Morpho USDC sur Base — dépôt/retrait direct on-chain.',
      curator: 'Steakhouse Financial',
      sortOrder: 0,
      isPublished: true,
      createdAt: now,
      updatedAt: now,
    },
  ]
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
