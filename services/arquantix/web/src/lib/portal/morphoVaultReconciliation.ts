import type { PortalMorphoVaultConfig, Prisma } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import { MORPHO_CHAIN_ID, normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import { fetchMorphoVaultPosition } from '@/lib/portal/morphoGraphql'
import { computePrincipalNetFromLedgerRows } from '@/lib/portal/morphoVaultLedger'
import { listPublishedPortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'
import {
  buildMorphoMonitoringAlerts,
  checkMorphoDependencyHealth,
  compareMorphoReconciliationAssets,
  computeMorphoGlobalStatus,
  isSignificantMismatchDelta,
} from '@/lib/portal/morphoVaultMonitoring'
import { getMorphoPendingAlertMinutes } from '@/lib/portal/morphoReconciliationConfig'
import { fetchPrivyEarnVaultPosition } from '@/lib/portal/privyServerClient'
import { getMorphoBetaDashboardStats } from '@/lib/portal/morphoBetaDashboard'
import {
  emitMorphoReconciliationMismatchLog,
  emitMorphoStalePendingSupportLogs,
} from '@/lib/portal/morphoBetaSupportEmit'

export type MorphoReconciliationRunSummary = {
  runId: string
  itemsChecked: number
  matchedCount: number
  mismatchCount: number
  missingOnchainCount: number
  missingLedgerCount: number
  startedAt: string
  finishedAt: string
}

type WalletVaultPair = {
  personId: string
  vaultAddress: string
  walletAddress: string
  privyWalletId: string | null
  integrationMode: string
}

async function loadWalletVaultPairs(configs: PortalMorphoVaultConfig[]): Promise<WalletVaultPair[]> {
  const vaultAddresses = configs.map((row) => normalizeVaultAddress(row.vaultAddress))
  const txRows = await prisma.onchainVaultTransaction.findMany({
    where: { vaultAddress: { in: vaultAddresses } },
    select: {
      personId: true,
      vaultAddress: true,
      walletAddress: true,
      privyWalletId: true,
      integrationMode: true,
    },
    distinct: ['personId', 'vaultAddress', 'walletAddress'],
  })

  const positionRows = await prisma.userVaultPosition.findMany({
    where: { vaultAddress: { in: vaultAddresses } },
    select: {
      personId: true,
      vaultAddress: true,
      walletAddress: true,
      privyWalletId: true,
    },
  })

  const map = new Map<string, WalletVaultPair>()
  for (const row of [...txRows, ...positionRows]) {
    const config = configs.find(
      (cfg) => normalizeVaultAddress(cfg.vaultAddress) === normalizeVaultAddress(row.vaultAddress),
    )
    const key = `${row.personId}:${normalizeVaultAddress(row.vaultAddress)}:${row.walletAddress.toLowerCase()}`
    map.set(key, {
      personId: row.personId,
      vaultAddress: normalizeVaultAddress(row.vaultAddress),
      walletAddress: row.walletAddress.toLowerCase(),
      privyWalletId: row.privyWalletId ?? null,
      integrationMode: config?.integrationMode ?? 'direct_morpho',
    })
  }
  return [...map.values()]
}

async function fetchOnchainPosition(args: {
  config: PortalMorphoVaultConfig
  walletAddress: string
  privyWalletId: string | null
}): Promise<{ assetsRaw: string; sharesRaw: string } | null> {
  if (args.config.integrationMode === 'privy_earn' && args.privyWalletId && args.config.privyVaultId) {
    try {
      const row = await fetchPrivyEarnVaultPosition(args.privyWalletId, args.config.privyVaultId)
      return {
        assetsRaw: String(row.assets_in_vault ?? row.assetsInVault ?? '0'),
        sharesRaw: String(row.shares_in_vault ?? row.sharesInVault ?? '0'),
      }
    } catch {
      return null
    }
  }

  const row = await fetchMorphoVaultPosition({
    vaultAddress: args.config.vaultAddress,
    walletAddress: args.walletAddress,
    chainId: args.config.chainId,
  })
  if (!row) return null
  return {
    assetsRaw: row.assets || '0',
    sharesRaw: row.shares || '0',
  }
}

/** Job de réconciliation ledger ↔ on-chain (Morpho GraphQL / Privy Earn). */
export async function runMorphoVaultReconciliation(): Promise<MorphoReconciliationRunSummary> {
  const startedAt = new Date()
  const configs = await listPublishedPortalMorphoVaultConfigs()
  const pairs = await loadWalletVaultPairs(configs)

  const run = await prisma.morphoVaultReconciliationRun.create({
    data: { startedAt },
  })

  let matchedCount = 0
  let mismatchCount = 0
  let missingOnchainCount = 0
  let missingLedgerCount = 0
  const logs: Array<Record<string, unknown>> = []

  for (const pair of pairs) {
    const config = configs.find(
      (row) => normalizeVaultAddress(row.vaultAddress) === pair.vaultAddress,
    )
    if (!config) continue

    const ledgerRows = await prisma.onchainVaultTransaction.findMany({
      where: {
        personId: pair.personId,
        vaultAddress: pair.vaultAddress,
        walletAddress: pair.walletAddress,
        status: 'success',
        operation: { in: ['deposit', 'withdraw'] },
      },
      select: { operation: true, amountRaw: true, status: true },
    })

    const position = await prisma.userVaultPosition.findFirst({
      where: {
        personId: pair.personId,
        vaultAddress: pair.vaultAddress,
        walletAddress: pair.walletAddress,
      },
    })

    const onchain = await fetchOnchainPosition({
      config,
      walletAddress: pair.walletAddress,
      privyWalletId: pair.privyWalletId,
    })

    const ledgerAssetsRaw = position?.lastAssetsRaw
      ?? (ledgerRows.length > 0 ? computePrincipalNetFromLedgerRows(ledgerRows).toString() : '0')
    const onchainAssetsRaw = onchain?.assetsRaw ?? '0'
    const status = compareMorphoReconciliationAssets({ ledgerAssetsRaw, onchainAssetsRaw })

    const deltaAssetsRaw = (
      BigInt(onchainAssetsRaw || '0') - BigInt(ledgerAssetsRaw || '0')
    ).toString()

    if (status === 'matched') matchedCount += 1
    if (status === 'mismatch') mismatchCount += 1
    if (status === 'missing_onchain') missingOnchainCount += 1
    if (status === 'missing_ledger') missingLedgerCount += 1

    await prisma.morphoVaultReconciliationItem.create({
      data: {
        runId: run.id,
        personId: pair.personId,
        vaultAddress: pair.vaultAddress,
        walletAddress: pair.walletAddress,
        privyWalletId: pair.privyWalletId,
        integrationMode: pair.integrationMode,
        status,
        ledgerAssetsRaw,
        onchainAssetsRaw,
        deltaAssetsRaw,
        ledgerSharesRaw: position?.lastSharesRaw ?? null,
        onchainSharesRaw: onchain?.sharesRaw ?? null,
        deltaSharesRaw:
          onchain?.sharesRaw && position?.lastSharesRaw
            ? (BigInt(onchain.sharesRaw) - BigInt(position.lastSharesRaw)).toString()
            : null,
        detailsJson: {
          chainId: config.chainId ?? MORPHO_CHAIN_ID,
          costBasisUnknown: position?.costBasisUnknown ?? false,
          principalNetRaw: position?.principalNetRaw ?? null,
        },
      },
    })

    if (status !== 'matched') {
      logs.push({
        personId: pair.personId,
        vaultAddress: pair.vaultAddress,
        walletAddress: pair.walletAddress,
        status,
        deltaAssetsRaw,
      })
      emitMorphoReconciliationMismatchLog({
        personId: pair.personId,
        vaultAddress: pair.vaultAddress,
        walletAddress: pair.walletAddress,
        status,
        deltaAssetsRaw,
      })
    }
  }

  const finishedAt = new Date()
  await prisma.morphoVaultReconciliationRun.update({
    where: { id: run.id },
    data: {
      finishedAt,
      itemsChecked: pairs.length,
      matchedCount,
      mismatchCount,
      missingOnchainCount,
      missingLedgerCount,
      logJson: logs as Prisma.InputJsonValue,
    },
  })

  const pendingMinutes = getMorphoPendingAlertMinutes()
  const pendingCutoff = new Date(Date.now() - pendingMinutes * 60_000)
  const stalePending = await prisma.onchainVaultTransaction.findMany({
    where: { status: 'pending', createdAt: { lte: pendingCutoff } },
    select: {
      id: true,
      personId: true,
      vaultAddress: true,
      operation: true,
      createdAt: true,
      txHash: true,
    },
    take: 100,
  })
  if (stalePending.length > 0) {
    emitMorphoStalePendingSupportLogs(stalePending)
  }

  return {
    runId: run.id,
    itemsChecked: pairs.length,
    matchedCount,
    mismatchCount,
    missingOnchainCount,
    missingLedgerCount,
    startedAt: startedAt.toISOString(),
    finishedAt: finishedAt.toISOString(),
  }
}

export async function getLatestMorphoReconciliationRun() {
  return prisma.morphoVaultReconciliationRun.findFirst({
    orderBy: { startedAt: 'desc' },
    include: {
      items: {
        where: { status: { not: 'matched' } },
        orderBy: { createdAt: 'desc' },
        take: 50,
      },
    },
  })
}

export async function getMorphoMonitoringSnapshot(args?: { pendingMinutes?: number }) {
  const pendingMinutes = args?.pendingMinutes ?? getMorphoPendingAlertMinutes()
  const pendingCutoff = new Date(Date.now() - pendingMinutes * 60_000)

  const [registry, allRegistry, publishedConfigs, pendingTxs, positions, latestRun, dependencyHealth] =
    await Promise.all([
    prisma.defiVaultRegistry.findMany({
      where: { isActive: true },
      orderBy: [{ chainId: 'asc' }, { vaultAddress: 'asc' }],
    }),
    prisma.defiVaultRegistry.findMany({
      select: { vaultAddress: true, isActive: true, lastSyncedAt: true },
    }),
    listPublishedPortalMorphoVaultConfigs(),
    prisma.onchainVaultTransaction.findMany({
      where: {
        status: 'pending',
        createdAt: { lte: pendingCutoff },
      },
      orderBy: { createdAt: 'asc' },
      take: 100,
    }),
    prisma.userVaultPosition.findMany({
      select: {
        vaultAddress: true,
        lastAssetsRaw: true,
        assetSymbol: true,
        costBasisUnknown: true,
      },
    }),
    getLatestMorphoReconciliationRun(),
    checkMorphoDependencyHealth(),
  ])

  const assetsByVault = new Map<string, bigint>()
  let costBasisUnknownCount = 0
  for (const row of positions) {
    const current = assetsByVault.get(row.vaultAddress) ?? BigInt(0)
    assetsByVault.set(row.vaultAddress, current + BigInt(row.lastAssetsRaw || '0'))
    if (row.costBasisUnknown) costBasisUnknownCount += 1
  }

  const inactiveRegistryVaultsCount = publishedConfigs.filter((config) => {
    const row = allRegistry.find(
      (entry) => entry.vaultAddress.toLowerCase() === config.vaultAddress.toLowerCase(),
    )
    return !row || !row.isActive
  }).length

  const mismatches = latestRun?.items ?? []
  const significantMismatchCount = mismatches.filter(
    (row) => row.status === 'mismatch' && isSignificantMismatchDelta(row.deltaAssetsRaw),
  ).length

  const alerts = buildMorphoMonitoringAlerts({
    pendingTransactionsCount: pendingTxs.length,
    pendingThresholdMinutes: pendingMinutes,
    mismatchCount: latestRun?.mismatchCount ?? 0,
    significantMismatchCount,
    missingOnchainCount: latestRun?.missingOnchainCount ?? 0,
    missingLedgerCount: latestRun?.missingLedgerCount ?? 0,
    inactiveRegistryVaultsCount,
    dependencyHealth,
  })

  const globalStatus = computeMorphoGlobalStatus(alerts)

  const beta = await getMorphoBetaDashboardStats({
    mismatchCount: latestRun?.mismatchCount ?? 0,
    pendingTxCount: pendingTxs.length,
  })

  return {
    globalStatus,
    alerts,
    dependencyHealth,
    beta,
    activeVaults: registry.map((row) => ({
      vaultAddress: row.vaultAddress,
      name: row.name,
      assetSymbol: row.assetSymbol,
      integrationMode: row.integrationMode,
      lastSyncedAt: row.lastSyncedAt?.toISOString() ?? null,
      trackedAssetsRaw: assetsByVault.get(row.vaultAddress)?.toString() ?? '0',
    })),
    pendingTransactions: pendingTxs.map((row) => ({
      id: row.id,
      personId: row.personId,
      vaultAddress: row.vaultAddress,
      operation: row.operation,
      integrationMode: row.integrationMode,
      createdAt: row.createdAt.toISOString(),
      idempotencyKey: row.idempotencyKey,
    })),
    pendingThresholdMinutes: pendingMinutes,
    costBasisUnknownCount,
    latestReconciliation: latestRun
      ? {
          runId: latestRun.id,
          startedAt: latestRun.startedAt.toISOString(),
          finishedAt: latestRun.finishedAt?.toISOString() ?? null,
          itemsChecked: latestRun.itemsChecked,
          matchedCount: latestRun.matchedCount,
          mismatchCount: latestRun.mismatchCount,
          missingOnchainCount: latestRun.missingOnchainCount,
          missingLedgerCount: latestRun.missingLedgerCount,
          mismatches: latestRun.items,
        }
      : null,
  }
}
