import type { PortalMorphoVaultConfig } from '@prisma/client'

import { normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import type { MorphoVaultPositionRow } from '@/lib/portal/morphoGraphql'
import type {
  PortalMorphoCatalogVault,
  PortalMorphoVaultDetails,
  PortalMorphoVaultPosition,
} from '@/lib/portal/morphoVaultTypes'
import {
  formatEarnApyFromBps,
  formatEarnTokenAmount,
  formatEarnUsd,
} from '@/lib/portal/privyEarnFormat'

function apyDecimalToBps(value: number | null | undefined): number | null {
  if (value == null || !Number.isFinite(value)) return null
  return Math.round(value * 10_000)
}

export function mergeMorphoVaultConfigWithGraphql(
  config: PortalMorphoVaultConfig,
  gql?: PortalMorphoCatalogVault | null,
): PortalMorphoVaultDetails {
  const vaultAddress = config.vaultAddress
  const name = config.label?.trim() || gql?.name || 'Vault Morpho'
  const description = config.description?.trim() || gql?.description || null
  const asset = gql?.asset ?? { address: '', symbol: 'USDC', decimals: 6 }

  return {
    id:
      config.integrationMode === 'privy_earn' && config.privyVaultId
        ? config.privyVaultId
        : normalizeVaultAddress(vaultAddress),
    vaultAddress,
    chainId: config.chainId,
    integrationMode: config.integrationMode,
    privyVaultId: config.privyVaultId,
    name,
    provider: 'morpho',
    asset,
    userApyBps: apyDecimalToBps(gql?.netApy),
    tvlUsd: gql?.tvlUsd ?? null,
    availableLiquidityUsd: gql?.liquidityUsd ?? gql?.tvlUsd ?? null,
    morphoVaultVersion: gql?.version ?? null,
    label: config.label,
    description,
    curator: config.curator ?? gql?.curator ?? null,
    listed: gql?.listed,
  }
}

export function mapMorphoVaultPosition(
  row: MorphoVaultPositionRow,
  vaultAddress: string,
  options?: {
    principalNetRaw?: string | null
    costBasisUnknown?: boolean
  },
): PortalMorphoVaultPosition {
  const { asset } = row
  const assetsInVault = row.assets || '0'
  const earnedYieldDisplay =
    options?.costBasisUnknown || options?.principalNetRaw == null
      ? computeEarnedYieldDisplay({
          currentAssetsRaw: assetsInVault,
          principalNetRaw: null,
          asset,
        })
      : computeEarnedYieldDisplay({
          currentAssetsRaw: assetsInVault,
          principalNetRaw: options.principalNetRaw,
          asset,
        })
  return {
    vaultAddress,
    asset,
    assetsInVault,
    assetsInVaultDisplay: `${formatEarnTokenAmount(assetsInVault, asset.decimals)} ${asset.symbol}`,
    sharesInVault: row.shares || '0',
    assetsUsd: row.assetsUsd,
    earnedYieldDisplay,
    yieldSyncStatus:
      options?.costBasisUnknown || options?.principalNetRaw == null ? 'pending' : 'synced',
  }
}

export function computeEarnedYieldDisplay(args: {
  currentAssetsRaw: string
  principalNetRaw: string | null
  asset: { symbol: string; decimals: number }
}): string {
  if (args.principalNetRaw == null) {
    return 'Rendement en cours de synchronisation'
  }
  const current = BigInt(args.currentAssetsRaw || '0')
  const principal = BigInt(args.principalNetRaw || '0')
  const earned = current > principal ? current - principal : BigInt(0)
  return `${formatEarnTokenAmount(earned.toString(), args.asset.decimals)} ${args.asset.symbol}`
}

export function parseHumanAmountToRaw(amount: string, decimals: number): bigint {
  const normalized = amount.trim().replace(',', '.')
  if (!/^\d+(\.\d+)?$/.test(normalized)) {
    throw new Error('Montant invalide.')
  }
  const [wholePart, fractionPart = ''] = normalized.split('.')
  const paddedFraction = fractionPart.padEnd(decimals, '0').slice(0, decimals)
  const raw = `${wholePart}${paddedFraction}`.replace(/^0+(?=\d)/, '')
  return BigInt(raw || '0')
}

export function formatApyFromDecimal(value: number | null | undefined): string {
  return formatEarnApyFromBps(apyDecimalToBps(value))
}

export { formatEarnApyFromBps, formatEarnTokenAmount, formatEarnUsd }
