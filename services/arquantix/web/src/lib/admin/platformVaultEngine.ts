/**
 * Moteur VAULT_ENGINE — liaison produits packagés ↔ vaults plateforme (Morpho / Ledgity).
 *
 * Types éligibles : `VAULT_SIMPLE` (ex. Flex Vault, Morpho USDC) et `EXCLUSIVE_OFFER`.
 * La différenciation catalogue est marketing (Vault Builder + product_type) ; le moteur est le même.
 */
import type { PackagedProductType, PortalMorphoVaultConfig } from '@prisma/client'

import { fetchLedgityVaultCatalog } from '@/lib/portal/ledgity/ledgityVaultAdapter'
import { mergeLedgityVaultConfigWithCatalog } from '@/lib/portal/ledgity/ledgityVaultFormat'
import { resolvePortalLedgityVaultConfigs } from '@/lib/portal/ledgity/ledgityVaultConfigStore'
import { fetchMorphoVaultsByAddresses } from '@/lib/portal/morphoGraphql'
import { mergeMorphoVaultConfigWithGraphql } from '@/lib/portal/morphoVaultFormat'
import { resolvePortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'
import {
  ledgityLockStateToSnapshotFields,
  readLedgityVaultLockState,
} from '@/lib/portal/ledgity/ledgityVaultLock'
import { prisma } from '@/lib/prisma'

export type { VaultEngineSnapshot } from '@/lib/admin/platformVaultEngineTypes'
import type { VaultEngineSnapshot } from '@/lib/admin/platformVaultEngineTypes'

export type PlatformVaultAdminRow = {
  portalConfigId: string
  provider: 'morpho' | 'ledgity'
  integrationMode: string
  vaultAddress: string
  chainId: number
  label: string
  description: string | null
  curator: string | null
  assetSymbol: string
  userApyBps: number | null
  tvlUsd: number | null
  availableLiquidityUsd: number | null
  isPublished: boolean
  sortOrder: number
}

function apyBpsToPct(bps: number | null): number | null {
  if (bps == null || !Number.isFinite(bps)) return null
  return bps / 100
}

function liquidityPct(tvlUsd: number | null, liquidityUsd: number | null): number | null {
  if (tvlUsd == null || liquidityUsd == null || !Number.isFinite(tvlUsd) || tvlUsd <= 0) {
    return null
  }
  return Math.min(100, Math.max(0, (liquidityUsd / tvlUsd) * 100))
}

async function enrichMorphoRows(configs: PortalMorphoVaultConfig[]): Promise<PlatformVaultAdminRow[]> {
  if (configs.length === 0) return []
  const gqlRows = await fetchMorphoVaultsByAddresses({
    addresses: configs.map((c) => c.vaultAddress),
  }).catch(() => [])
  const gqlByAddress = new Map(gqlRows.map((row) => [row.address.toLowerCase(), row]))

  return configs.map((config) => {
    const merged = mergeMorphoVaultConfigWithGraphql(
      config,
      gqlByAddress.get(config.vaultAddress.toLowerCase()),
    )
    return {
      portalConfigId: config.id,
      provider: 'morpho' as const,
      integrationMode: config.integrationMode,
      vaultAddress: config.vaultAddress,
      chainId: config.chainId,
      label: merged.name,
      description: merged.description ?? null,
      curator: merged.curator ?? null,
      assetSymbol: merged.asset.symbol,
      userApyBps: merged.userApyBps,
      tvlUsd: merged.tvlUsd,
      availableLiquidityUsd: merged.availableLiquidityUsd,
      isPublished: config.isPublished,
      sortOrder: config.sortOrder,
    }
  })
}

async function enrichLedgityRows(configs: PortalMorphoVaultConfig[]): Promise<PlatformVaultAdminRow[]> {
  if (configs.length === 0) return []
  const catalogs = await fetchLedgityVaultCatalog({
    addresses: configs.map((c) => c.vaultAddress),
  }).catch(() => [])
  const catalogByAddress = new Map(catalogs.map((row) => [row.address.toLowerCase(), row]))

  return configs.map((config) => {
    const merged = mergeLedgityVaultConfigWithCatalog(
      config,
      catalogByAddress.get(config.vaultAddress.toLowerCase()),
    )
    return {
      portalConfigId: config.id,
      provider: 'ledgity' as const,
      integrationMode: config.integrationMode,
      vaultAddress: config.vaultAddress,
      chainId: config.chainId,
      label: merged.name,
      description: merged.description ?? null,
      curator: merged.curator ?? null,
      assetSymbol: merged.asset.symbol,
      userApyBps: merged.userApyBps,
      tvlUsd: merged.tvlUsd,
      availableLiquidityUsd: merged.availableLiquidityUsd,
      isPublished: config.isPublished,
      sortOrder: config.sortOrder,
    }
  })
}

/** Liste des vaults plateforme disponibles pour liaison admin (Morpho + Ledgity). */
export async function listAvailablePlatformVaultsForAdmin(options?: {
  publishedOnly?: boolean
  query?: string
  limit?: number
}): Promise<PlatformVaultAdminRow[]> {
  const publishedOnly = options?.publishedOnly ?? false
  const limit = Math.min(Math.max(options?.limit ?? 50, 1), 200)
  const q = options?.query?.trim().toLowerCase() ?? ''

  const [morphoConfigs, ledgityConfigs] = await Promise.all([
    resolvePortalMorphoVaultConfigs({ publishedOnly }),
    resolvePortalLedgityVaultConfigs({ publishedOnly }),
  ])

  const [morphoRows, ledgityRows] = await Promise.all([
    enrichMorphoRows(morphoConfigs),
    enrichLedgityRows(ledgityConfigs),
  ])

  let rows = [...morphoRows, ...ledgityRows].sort((a, b) => a.sortOrder - b.sortOrder || a.label.localeCompare(b.label))

  if (q) {
    rows = rows.filter(
      (row) =>
        row.label.toLowerCase().includes(q) ||
        row.vaultAddress.toLowerCase().includes(q) ||
        row.portalConfigId.toLowerCase().includes(q) ||
        row.assetSymbol.toLowerCase().includes(q) ||
        row.provider.includes(q),
    )
  }

  return rows.slice(0, limit)
}

export async function resolvePlatformVaultAdminRow(
  portalConfigId: string,
): Promise<PlatformVaultAdminRow | null> {
  const config = await prisma.portalMorphoVaultConfig.findUnique({
    where: { id: portalConfigId },
  })
  if (!config) return null

  const mode = String(config.integrationMode)
  if (mode === 'ledgity_vault') {
    const rows = await enrichLedgityRows([config])
    return rows[0] ?? null
  }
  const rows = await enrichMorphoRows([config])
  return rows[0] ?? null
}

export function buildVaultEngineSnapshot(row: PlatformVaultAdminRow): VaultEngineSnapshot {
  const supplyApr = apyBpsToPct(row.userApyBps)
  const liqPct = liquidityPct(row.tvlUsd, row.availableLiquidityUsd)

  return {
    status: row.isPublished ? 'published' : 'draft',
    investable: row.isPublished,
    provider: row.provider,
    integration_mode: row.integrationMode,
    portal_config_id: row.portalConfigId,
    vault_address: row.vaultAddress,
    chain_id: row.chainId,
    name: row.label,
    asset: row.assetSymbol,
    asset_symbol: row.assetSymbol,
    user_apy_bps: row.userApyBps,
    supply_apr: supplyApr,
    tvl_usd: row.tvlUsd,
    available_liquidity_usd: row.availableLiquidityUsd,
    liquidity_pct: liqPct,
    curator: row.curator,
  }
}

export async function fetchVaultEngineSnapshot(
  portalConfigId: string,
): Promise<VaultEngineSnapshot | null> {
  const row = await resolvePlatformVaultAdminRow(portalConfigId)
  if (!row) return null
  const snap = buildVaultEngineSnapshot(row)
  if (row.provider !== 'ledgity') return snap
  try {
    const lock = await readLedgityVaultLockState({ vaultAddress: row.vaultAddress })
    return { ...snap, ...ledgityLockStateToSnapshotFields(lock) } as VaultEngineSnapshot
  } catch (error) {
    console.error('[platformVaultEngine] lock snapshot enrichment failed', {
      portalConfigId,
      vaultAddress: row.vaultAddress,
      error,
    })
    return snap
  }
}

export function isVaultEngineLinked(engineType: string | null, engineReferenceId: string | null): boolean {
  return engineType === 'VAULT_ENGINE' && Boolean(engineReferenceId?.trim())
}

/** Types produit autorisés à connecter un vault plateforme (capability matrix Phase 9). */
export const VAULT_ENGINE_ELIGIBLE_PRODUCT_TYPES: PackagedProductType[] = [
  'VAULT_SIMPLE',
  'EXCLUSIVE_OFFER',
]

export function isVaultEngineEligibleProductType(productType: string | null | undefined): boolean {
  if (!productType) return false
  return (VAULT_ENGINE_ELIGIBLE_PRODUCT_TYPES as string[]).includes(productType)
}
