import type {
  PortalEarnVaultDetails,
  PortalEarnVaultPosition,
  PortalEarnWalletAction,
} from '@/lib/portal/privyEarnTypes'
import type { PortalEarnVaultConfig } from '@/lib/portal/privyEarnConfig'

function toNumber(value: unknown): number | null {
  if (value == null) return null
  const n = typeof value === 'number' ? value : Number(String(value))
  return Number.isFinite(n) ? n : null
}

function toStringValue(value: unknown, fallback = '0'): string {
  if (value == null) return fallback
  const s = String(value).trim()
  return s || fallback
}

export function formatEarnTokenAmount(raw: string, decimals: number, maxFraction = 4): string {
  const value = BigInt(raw || '0')
  const base = BigInt(10) ** BigInt(Math.max(0, decimals))
  const whole = value / base
  const fraction = value % base
  if (fraction === BigInt(0)) return whole.toString()
  const fracStr = fraction.toString().padStart(decimals, '0').replace(/0+$/, '')
  const trimmed = fracStr.slice(0, maxFraction).replace(/0+$/, '')
  return trimmed ? `${whole}.${trimmed}` : whole.toString()
}

export function formatEarnApyFromBps(bps: number | null): string {
  if (bps == null || !Number.isFinite(bps)) return '—'
  return `${(bps / 100).toFixed(2)}%`
}

export function formatEarnUsd(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return '—'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

export function mapPrivyEarnVaultDetails(
  row: Record<string, unknown>,
  config?: PortalEarnVaultConfig,
): PortalEarnVaultDetails {
  const assetRaw = (row.asset ?? {}) as Record<string, unknown>
  const asset = {
    address: toStringValue(assetRaw.address),
    symbol: toStringValue(assetRaw.symbol, 'usdc').toUpperCase(),
    decimals: toNumber(assetRaw.decimals) ?? 6,
  }
  return {
    id: toStringValue(row.id),
    name: config?.label ?? toStringValue(row.name, 'Vault Earn'),
    provider: toStringValue(row.provider, 'morpho'),
    vaultAddress: toStringValue(row.vault_address ?? row.vaultAddress),
    asset,
    caip2: toStringValue(row.caip2),
    userApyBps: toNumber(row.user_apy ?? row.userApy),
    tvlUsd: toNumber(row.tvl_usd ?? row.tvlUsd),
    availableLiquidityUsd: toNumber(row.available_liquidity_usd ?? row.availableLiquidityUsd),
    label: config?.label,
    description: config?.description,
  }
}

export function mapPrivyEarnVaultPosition(
  row: Record<string, unknown>,
  vaultId: string,
): PortalEarnVaultPosition {
  const assetRaw = (row.asset ?? {}) as Record<string, unknown>
  const decimals = toNumber(assetRaw.decimals) ?? 6
  const symbol = toStringValue(assetRaw.symbol, 'usdc').toUpperCase()
  const assetsInVault = toStringValue(row.assets_in_vault ?? row.assetsInVault)
  const totalDeposited = toStringValue(row.total_deposited ?? row.totalDeposited)
  const totalWithdrawn = toStringValue(row.total_withdrawn ?? row.totalWithdrawn)

  const assetsBig = BigInt(assetsInVault || '0')
  const netDeposited = BigInt(totalDeposited || '0') - BigInt(totalWithdrawn || '0')
  const earnedRaw = assetsBig > netDeposited ? assetsBig - netDeposited : BigInt(0)

  return {
    vaultId,
    asset: {
      address: toStringValue(assetRaw.address),
      symbol,
      decimals,
    },
    assetsInVault,
    assetsInVaultDisplay: `${formatEarnTokenAmount(assetsInVault, decimals)} ${symbol}`,
    totalDeposited,
    totalWithdrawn,
    earnedYieldDisplay: `${formatEarnTokenAmount(earnedRaw.toString(), decimals)} ${symbol}`,
    sharesInVault: toStringValue(row.shares_in_vault ?? row.sharesInVault),
  }
}

function extractTxHash(steps: unknown): string | null {
  if (!Array.isArray(steps)) return null
  for (const step of steps) {
    if (!step || typeof step !== 'object') continue
    const row = step as Record<string, unknown>
    const hash = row.transaction_hash ?? row.transactionHash ?? row.bundle_transaction_hash
    if (typeof hash === 'string' && hash.trim()) return hash.trim()
  }
  return null
}

export function mapPrivyEarnWalletAction(row: Record<string, unknown>): PortalEarnWalletAction {
  const failure = row.failure_reason as Record<string, unknown> | undefined
  return {
    id: toStringValue(row.id),
    status: toStringValue(row.status),
    type: toStringValue(row.type),
    walletId: toStringValue(row.wallet_id ?? row.walletId),
    vaultId: toStringValue(row.vault_id ?? row.vaultId, '') || undefined,
    amount: toStringValue(row.amount, '') || undefined,
    rawAmount: toStringValue(row.raw_amount ?? row.rawAmount, '') || undefined,
    asset: toStringValue(row.asset, '') || undefined,
    transactionHash: extractTxHash(row.steps),
    failureMessage:
      typeof failure?.message === 'string' ? failure.message : null,
  }
}
