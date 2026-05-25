import { prisma } from '@/lib/prisma'
import { normalizeVaultAddress } from '@/lib/portal/ledgity/ledgityConstants'
import {
  getLedgityBetaEmails,
  getLedgityBetaLimitsForClient,
  getLedgityBetaPersonIds,
  isLedgityBetaAllowAllUsers,
  isLedgityBetaEnabled,
  isLedgityDepositsDisabled,
  isLedgityWithdrawsDisabled,
} from '@/lib/portal/ledgity/ledgityConfig'
import { listPublishedPortalLedgityVaultConfigs } from '@/lib/portal/ledgity/ledgityVaultConfigStore'

export type LedgityBetaDashboardStats = {
  betaEnabled: boolean
  depositsDisabled: boolean
  withdrawsDisabled: boolean
  allowlistPersonIdsCount: number
  allowlistEmailsCount: number
  allowAllUsers: boolean
  betaActiveUsersCount: number
  totalDepositedRaw: string
  totalWithdrawnRaw: string
  totalAssetsRaw: string
  pendingTxCount: number
  failedTxCount: number
  mismatchesCount: number
  limits: ReturnType<typeof getLedgityBetaLimitsForClient> | null
}

function rawToHuman(raw: bigint, decimals = 6): number {
  return Number(raw) / 10 ** decimals
}

async function publishedVaultAddresses(): Promise<string[]> {
  const configs = await listPublishedPortalLedgityVaultConfigs()
  return configs.map((row) => normalizeVaultAddress(row.vaultAddress))
}

/** Métriques beta Ledgity pour le dashboard admin. */
export async function getLedgityBetaDashboardStats(args?: {
  mismatchCount?: number
  pendingTxCount?: number
}): Promise<LedgityBetaDashboardStats> {
  const vaults = await publishedVaultAddresses()
  const vaultFilter =
    vaults.length > 0
      ? { vaultAddress: { in: vaults }, integrationMode: 'ledgity_vault' }
      : { vaultAddress: '__none__', integrationMode: 'ledgity_vault' }

  const [txPersonIds, positionPersonIds, depositRows, withdrawRows, positions, failedCount, pendingCount] =
    await Promise.all([
      prisma.onchainVaultTransaction.findMany({
        where: vaultFilter,
        select: { personId: true },
        distinct: ['personId'],
      }),
      prisma.userVaultPosition.findMany({
        where: { vaultAddress: vaultFilter.vaultAddress },
        select: { personId: true },
        distinct: ['personId'],
      }),
      prisma.onchainVaultTransaction.findMany({
        where: { ...vaultFilter, operation: 'deposit', status: 'success' },
        select: { amountRaw: true },
      }),
      prisma.onchainVaultTransaction.findMany({
        where: { ...vaultFilter, operation: 'withdraw', status: 'success' },
        select: { amountRaw: true },
      }),
      prisma.userVaultPosition.findMany({
        where: { vaultAddress: vaultFilter.vaultAddress },
        select: { lastAssetsRaw: true },
      }),
      prisma.onchainVaultTransaction.count({
        where: { ...vaultFilter, status: { in: ['failed', 'reverted'] } },
      }),
      args?.pendingTxCount ??
        prisma.onchainVaultTransaction.count({
          where: { ...vaultFilter, status: 'pending' },
        }),
    ])

  const activeUsers = new Set([
    ...txPersonIds.map((row) => row.personId),
    ...positionPersonIds.map((row) => row.personId),
  ])

  const totalDeposited = depositRows.reduce((acc, row) => acc + BigInt(row.amountRaw || '0'), BigInt(0))
  const totalWithdrawn = withdrawRows.reduce((acc, row) => acc + BigInt(row.amountRaw || '0'), BigInt(0))
  const totalAssets = positions.reduce((acc, row) => acc + BigInt(row.lastAssetsRaw || '0'), BigInt(0))

  return {
    betaEnabled: isLedgityBetaEnabled(),
    depositsDisabled: isLedgityDepositsDisabled(),
    withdrawsDisabled: isLedgityWithdrawsDisabled(),
    allowlistPersonIdsCount: getLedgityBetaPersonIds().size,
    allowlistEmailsCount: getLedgityBetaEmails().size,
    allowAllUsers: isLedgityBetaAllowAllUsers(),
    betaActiveUsersCount: activeUsers.size,
    totalDepositedRaw: totalDeposited.toString(),
    totalWithdrawnRaw: totalWithdrawn.toString(),
    totalAssetsRaw: totalAssets.toString(),
    pendingTxCount: typeof pendingCount === 'number' ? pendingCount : 0,
    failedTxCount: failedCount,
    mismatchesCount: args?.mismatchCount ?? 0,
    limits: getLedgityBetaLimitsForClient(),
  }
}

export function formatLedgityBetaDashboardForClient(stats: LedgityBetaDashboardStats) {
  return {
    ...stats,
    totalDepositedUsdc: rawToHuman(BigInt(stats.totalDepositedRaw)),
    totalWithdrawnUsdc: rawToHuman(BigInt(stats.totalWithdrawnRaw)),
    totalAssetsInVaultUsdc: rawToHuman(BigInt(stats.totalAssetsRaw)),
  }
}
