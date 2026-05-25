import type { PortalMorphoIntegrationMode, PortalMorphoVaultConfig } from '@prisma/client'

import {
  LEDGITY_LYEURC_VAULT,
  LEDGITY_LYUSDC_VAULT,
  normalizeVaultAddress,
} from '@/lib/portal/ledgity/ledgityConstants'
import { prisma } from '@/lib/prisma'

const LEDGITY_VAULT_ONLY = 'ledgity_vault' as PortalMorphoIntegrationMode

function filterLedgityVaultConfigs(rows: PortalMorphoVaultConfig[]): PortalMorphoVaultConfig[] {
  return rows.filter((row) => (row.integrationMode as string) === LEDGITY_VAULT_ONLY)
}

export async function listPortalLedgityVaultConfigs(): Promise<PortalMorphoVaultConfig[]> {
  return filterLedgityVaultConfigs(
    await prisma.portalMorphoVaultConfig.findMany({
      orderBy: [{ sortOrder: 'asc' }, { createdAt: 'asc' }],
    }),
  )
}

export async function listPublishedPortalLedgityVaultConfigs(): Promise<PortalMorphoVaultConfig[]> {
  return filterLedgityVaultConfigs(
    await prisma.portalMorphoVaultConfig.findMany({
      where: { isPublished: true, integrationMode: LEDGITY_VAULT_ONLY },
      orderBy: [{ sortOrder: 'asc' }, { createdAt: 'asc' }],
    }),
  )
}

/** Fallback env-only quand la table est vide (dev). */
export function getEnvFallbackLedgityVaultConfigs(): PortalMorphoVaultConfig[] {
  const now = new Date()
  return [
    {
      id: 'env-ledgity-lyusdc',
      vaultAddress: normalizeVaultAddress(LEDGITY_LYUSDC_VAULT),
      chainId: 8453,
      integrationMode: LEDGITY_VAULT_ONLY,
      privyVaultId: null,
      label: 'Ledgity lyUSDC',
      description: 'Vault Ledgity lyUSDC sur Base — dépôt/retrait ERC4626 direct on-chain.',
      curator: 'Ledgity',
      sortOrder: 0,
      isPublished: true,
      createdAt: now,
      updatedAt: now,
    },
    {
      id: 'env-ledgity-lyeurc',
      vaultAddress: normalizeVaultAddress(LEDGITY_LYEURC_VAULT),
      chainId: 8453,
      integrationMode: LEDGITY_VAULT_ONLY,
      privyVaultId: null,
      label: 'Ledgity lyEURC',
      description: 'Vault Ledgity lyEURC sur Base — dépôt/retrait ERC4626 direct on-chain.',
      curator: 'Ledgity',
      sortOrder: 1,
      isPublished: true,
      createdAt: now,
      updatedAt: now,
    },
  ]
}

export async function resolvePortalLedgityVaultConfigs(options?: {
  publishedOnly?: boolean
}): Promise<PortalMorphoVaultConfig[]> {
  const rows = options?.publishedOnly
    ? await listPublishedPortalLedgityVaultConfigs()
    : await listPortalLedgityVaultConfigs()
  if (rows.length) return rows
  return getEnvFallbackLedgityVaultConfigs()
}
