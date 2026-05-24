import { prisma } from '@/lib/prisma'
import { listPublishedPortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'
import { normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import {
  getMorphoUsdcBetaEmails,
  getMorphoUsdcBetaPersonIds,
  isMorphoUsdcBetaAllowAllUsers,
  isMorphoUsdcBetaEnabled,
  isMorphoUsdcDepositsDisabled,
  isMorphoUsdcWithdrawsDisabled,
  getMorphoUsdcBetaLimitsForClient,
} from '@/lib/portal/morphoUsdcBetaConfig'

export type MorphoBetaDashboardStats = {
  betaEnabled: boolean
  depositsDisabled: boolean
  withdrawsDisabled: boolean
  allowlistPersonIdsCount: number
  allowlistEmailsCount: number
  allowAllUsers: boolean
  betaActiveUsersCount: number
  totalDepositedUsdc: number
  totalWithdrawnUsdc: number
  totalAssetsInVaultUsdc: number
  totalEarnedYieldUsdc: number
  pendingTxCount: number
  failedTxCount: number
  mismatchesCount: number
  limits: ReturnType<typeof getMorphoUsdcBetaLimitsForClient> | null
}

function rawToUsdc(raw: bigint): number {
  return Number(raw) / 1_000_000
}

async function publishedVaultAddresses(): Promise<string[]> {
  const configs = await listPublishedPortalMorphoVaultConfigs()
  return configs.map((row) => normalizeVaultAddress(row.vaultAddress))
}

/** Métriques beta pour le dashboard admin Morpho. */
export async function getMorphoBetaDashboardStats(args?: {
  mismatchCount?: number
  pendingTxCount?: number
}): Promise<MorphoBetaDashboardStats> {
  const vaults = await publishedVaultAddresses()
  const vaultFilter = vaults.length > 0 ? { vaultAddress: { in: vaults } } : { vaultAddress: '__none__' }

  const [txPersonIds, positionPersonIds, depositRows, withdrawRows, positions, failedCount, pendingCount] =
    await Promise.all([
      prisma.onchainVaultTransaction.findMany({
        where: vaultFilter,
        select: { personId: true },
        distinct: ['personId'],
      }),
      prisma.userVaultPosition.findMany({
        where: vaultFilter,
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
        where: vaultFilter,
        select: {
          lastAssetsRaw: true,
          principalNetRaw: true,
          costBasisUnknown: true,
        },
      }),
      prisma.onchainVaultTransaction.count({
        where: { ...vaultFilter, status: { in: ['failed', 'reverted'] } },
      }),
      args?.pendingTxCount ??
        prisma.onchainVaultTransaction.count({
          where: { ...vaultFilter, status: 'pending' },
        }),
    ])

  const activePersonIds = new Set<string>()
  for (const row of txPersonIds) activePersonIds.add(row.personId)
  for (const row of positionPersonIds) activePersonIds.add(row.personId)

  let totalDepositedRaw = BigInt(0)
  for (const row of depositRows) totalDepositedRaw += BigInt(row.amountRaw || '0')

  let totalWithdrawnRaw = BigInt(0)
  for (const row of withdrawRows) totalWithdrawnRaw += BigInt(row.amountRaw || '0')

  let totalAssetsRaw = BigInt(0)
  let totalEarnedYieldRaw = BigInt(0)
  for (const row of positions) {
    const assets = BigInt(row.lastAssetsRaw || '0')
    totalAssetsRaw += assets
    if (!row.costBasisUnknown) {
      const principal = BigInt(row.principalNetRaw || '0')
      const yieldRaw = assets > principal ? assets - principal : BigInt(0)
      totalEarnedYieldRaw += yieldRaw
    }
  }

  const betaEnabled = isMorphoUsdcBetaEnabled()

  return {
    betaEnabled,
    depositsDisabled: isMorphoUsdcDepositsDisabled(),
    withdrawsDisabled: isMorphoUsdcWithdrawsDisabled(),
    allowlistPersonIdsCount: getMorphoUsdcBetaPersonIds().size,
    allowlistEmailsCount: getMorphoUsdcBetaEmails().size,
    allowAllUsers: isMorphoUsdcBetaAllowAllUsers(),
    betaActiveUsersCount: activePersonIds.size,
    totalDepositedUsdc: rawToUsdc(totalDepositedRaw),
    totalWithdrawnUsdc: rawToUsdc(totalWithdrawnRaw),
    totalAssetsInVaultUsdc: rawToUsdc(totalAssetsRaw),
    totalEarnedYieldUsdc: rawToUsdc(totalEarnedYieldRaw),
    pendingTxCount: typeof pendingCount === 'number' ? pendingCount : await pendingCount,
    failedTxCount: failedCount,
    mismatchesCount: args?.mismatchCount ?? 0,
    limits: betaEnabled ? getMorphoUsdcBetaLimitsForClient() : null,
  }
}
