import type { PortalMorphoVaultConfig } from '@prisma/client'

import {
  formatEarnApyFromBps,
  formatEarnTokenAmount,
} from '@/lib/portal/morphoVaultFormat'
import { normalizeVaultAddress } from '@/lib/portal/ledgity/ledgityConstants'
import type {
  LedgityVaultPositionRow,
  PortalLedgityCatalogVault,
  PortalLedgityVaultDetails,
  PortalLedgityVaultPosition,
} from '@/lib/portal/ledgity/ledgityVaultTypes'

export { formatEarnApyFromBps, formatEarnTokenAmount }

function apyDecimalToBps(value: number | null | undefined): number | null {
  if (value == null || !Number.isFinite(value)) return null
  return Math.round(value * 10_000)
}

export function mergeLedgityVaultConfigWithCatalog(
  config: PortalMorphoVaultConfig,
  catalog?: PortalLedgityCatalogVault | null,
): PortalLedgityVaultDetails {
  const vaultAddress = config.vaultAddress
  const name = config.label?.trim() || catalog?.name || 'Vault Ledgity'
  const description = config.description?.trim() || catalog?.description || null
  const asset = catalog?.asset ?? { address: '', symbol: 'USDC', decimals: 6 }

  return {
    id: normalizeVaultAddress(vaultAddress),
    vaultAddress,
    chainId: config.chainId,
    integrationMode: 'ledgity_vault',
    name,
    provider: 'ledgity',
    asset,
    userApyBps: apyDecimalToBps(catalog?.netApy),
    pricePerShare: catalog?.pricePerShare ?? null,
    tvlUsd: catalog?.tvlUsd ?? null,
    availableLiquidityUsd: catalog?.liquidityUsd ?? catalog?.tvlUsd ?? null,
    label: config.label,
    description,
    curator: config.curator ?? catalog?.curator ?? null,
    listed: catalog?.listed,
  }
}

export function computeLedgityYieldDisplay(args: {
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

export function mapLedgityVaultPosition(
  row: LedgityVaultPositionRow,
  vaultAddress: string,
  options?: {
    principalNetRaw?: string | null
    costBasisUnknown?: boolean
  },
): PortalLedgityVaultPosition {
  const { asset } = row
  const assetsInVault = row.assets || '0'
  const earnedYieldDisplay =
    options?.costBasisUnknown || options?.principalNetRaw == null
      ? computeLedgityYieldDisplay({
          currentAssetsRaw: assetsInVault,
          principalNetRaw: null,
          asset,
        })
      : computeLedgityYieldDisplay({
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

export function formatPricePerShare(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return '—'
  return value.toFixed(4)
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
