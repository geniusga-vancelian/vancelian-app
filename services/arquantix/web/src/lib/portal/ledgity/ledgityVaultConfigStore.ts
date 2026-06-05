import type { PortalMorphoIntegrationMode, PortalMorphoVaultConfig } from '@prisma/client'

import {
  LEDGITY_LYEURC_VAULT,
  LEDGITY_LYUSDC_VAULT,
  VANCELIAN_AXBALI_VAULT,
  VANCELIAN_AXDUBAI_VAULT,
  VANCELIAN_AXUSD_VAULT,
  VANCELIAN_VFEUR_VAULT,
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

type EnvFallbackSeed = {
  id: string
  vaultAddress: string
  label: string
  description: string
  curator: string
  sortOrder: number
}

const ENV_FALLBACK_SEEDS: EnvFallbackSeed[] = [
  {
    id: 'env-vancelian-vfeur',
    vaultAddress: VANCELIAN_VFEUR_VAULT,
    label: 'Vancelian Flexible Vault EURC',
    description: 'Coffre flexible vfEUR sur Base — ERC-4626 EURC.',
    curator: 'Vancelian',
    sortOrder: 1,
  },
  {
    id: 'env-vancelian-axusd',
    vaultAddress: VANCELIAN_AXUSD_VAULT,
    label: 'Arquantix Yield USDC',
    description: 'Coffre flexible axUSD sur Base — ERC-4626 USDC.',
    curator: 'Arquantix',
    sortOrder: 2,
  },
  {
    id: 'env-vancelian-axdubai',
    vaultAddress: VANCELIAN_AXDUBAI_VAULT,
    label: 'Arquantix Dubai',
    description: 'Offre exclusive RWA axDUBAI sur Base — ERC-4626 EURC.',
    curator: 'Arquantix',
    sortOrder: 3,
  },
  {
    id: 'env-vancelian-axbali',
    vaultAddress: VANCELIAN_AXBALI_VAULT,
    label: 'Arquantix Bali',
    description: 'Offre exclusive RWA axBALI sur Base — ERC-4626 EURC.',
    curator: 'Arquantix',
    sortOrder: 4,
  },
  {
    id: 'env-ledgity-lyusdc',
    vaultAddress: LEDGITY_LYUSDC_VAULT,
    label: 'Ledgity lyUSDC',
    description: 'Vault Ledgity lyUSDC sur Base — dépôt/retrait ERC4626 direct on-chain.',
    curator: 'Ledgity',
    sortOrder: 10,
  },
  {
    id: 'env-ledgity-lyeurc',
    vaultAddress: LEDGITY_LYEURC_VAULT,
    label: 'Ledgity lyEURC',
    description: 'Vault Ledgity lyEURC sur Base — dépôt/retrait ERC4626 direct on-chain.',
    curator: 'Ledgity',
    sortOrder: 11,
  },
]

/** Fallback env-only quand la table est vide (dev). */
export function getEnvFallbackLedgityVaultConfigs(): PortalMorphoVaultConfig[] {
  const now = new Date()
  return ENV_FALLBACK_SEEDS.map((seed) => ({
    id: seed.id,
    vaultAddress: normalizeVaultAddress(seed.vaultAddress),
    chainId: 8453,
    integrationMode: LEDGITY_VAULT_ONLY,
    privyVaultId: null,
    label: seed.label,
    description: seed.description,
    curator: seed.curator,
    sortOrder: seed.sortOrder,
    isPublished: true,
    createdAt: now,
    updatedAt: now,
  }))
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
