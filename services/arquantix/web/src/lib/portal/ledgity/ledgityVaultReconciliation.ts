import type { PortalMorphoVaultConfig, Prisma } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import { LEDGITY_CHAIN_ID, normalizeVaultAddress, resolveLedgityShareSymbol } from '@/lib/portal/ledgity/ledgityConstants'
import {
  formatLedgityBetaDashboardForClient,
  getLedgityBetaDashboardStats,
} from '@/lib/portal/ledgity/ledgityBetaDashboard'
import { isLedgityLocalSandboxEnabled } from '@/lib/portal/ledgity/ledgityLocalSandboxConfig'
import {
  fetchSandboxLedgityOnchainPositionForReconciliation,
} from '@/lib/portal/ledgity/mocks/ledgityLocalSandbox'
import { getLedgityPendingAlertMinutes } from '@/lib/portal/ledgity/ledgityReconciliationConfig'
import { listPublishedPortalLedgityVaultConfigs } from '@/lib/portal/ledgity/ledgityVaultConfigStore'
import {
  isLedgityLiquidityDeferred,
  isLedgityVaultLiquidityLow,
  isSignificantLedgityMismatchDelta,
  readLedgityWithdrawLiquidity,
  readLedgityVaultLiquidityMetrics,
} from '@/lib/portal/ledgity/ledgityVaultLiquidity'
import {
  buildLedgityMonitoringAlerts,
  checkLedgityDependencyHealth,
  compareLedgityReconciliationAssets,
  computeLedgityGlobalStatus,
  getLedgityRuntimeModeSnapshot,
  isLedgitySandboxEnabledInProduction,
} from '@/lib/portal/ledgity/ledgityVaultMonitoring'
import { fetchLedgityVaultCatalog } from '@/lib/portal/ledgity/ledgityVaultAdapter'
import { computePrincipalNetFromLedgerRows } from '@/lib/portal/morphoVaultLedger'

export type LedgityReconciliationRunSummary = {
  runId: string
  itemsChecked: number
  matchedCount: number
  mismatchCount: number
  missingOnchainCount: number
  missingLedgerCount: number
  ppsUnavailableCount: number
  liquidityWarningCount: number
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
    where: {
      vaultAddress: { in: vaultAddresses },
      integrationMode: 'ledgity_vault',
    },
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
    const key = `${row.personId}:${normalizeVaultAddress(row.vaultAddress)}:${row.walletAddress.toLowerCase()}`
    map.set(key, {
      personId: row.personId,
      vaultAddress: normalizeVaultAddress(row.vaultAddress),
      walletAddress: row.walletAddress.toLowerCase(),
      privyWalletId: row.privyWalletId ?? null,
      integrationMode: 'ledgity_vault',
    })
  }
  return [...map.values()]
}

async function fetchOnchainPosition(args: {
  config: PortalMorphoVaultConfig
  walletAddress: string
  personId: string
}): Promise<{ assetsRaw: string; sharesRaw: string; ppsAtReconcile: string | null } | null> {
  if (isLedgityLocalSandboxEnabled()) {
    return fetchSandboxLedgityOnchainPositionForReconciliation({
      personId: args.personId,
      vaultAddress: args.config.vaultAddress,
      walletAddress: args.walletAddress,
    })
  }

  const liquidity = await readLedgityWithdrawLiquidity({
    vaultAddress: args.config.vaultAddress,
    walletAddress: args.walletAddress,
    chainId: args.config.chainId,
  })
  if (!liquidity) return null

  return {
    assetsRaw: liquidity.assetsFromSharesRaw.toString(),
    sharesRaw: liquidity.sharesRaw.toString(),
    ppsAtReconcile: liquidity.pricePerShare != null ? String(liquidity.pricePerShare) : null,
  }
}

function resolveReconciliationStatus(args: {
  ledgerAssetsRaw: string
  onchainAssetsRaw: string
  ppsAtReconcile: string | null
  maxWithdrawRaw: bigint | null
  onchainAssetsBigInt: bigint
}): {
  status: ReturnType<typeof compareLedgityReconciliationAssets> | 'pps_unavailable' | 'liquidity_warning'
  ppsUnavailable: boolean
  liquidityWarning: boolean
} {
  if (args.ppsAtReconcile == null && args.onchainAssetsBigInt > BigInt(0)) {
    return { status: 'pps_unavailable', ppsUnavailable: true, liquidityWarning: false }
  }

  const baseStatus = compareLedgityReconciliationAssets({
    ledgerAssetsRaw: args.ledgerAssetsRaw,
    onchainAssetsRaw: args.onchainAssetsRaw,
  })

  const liquidityWarning =
    args.maxWithdrawRaw != null &&
    isLedgityLiquidityDeferred({
      maxWithdrawRaw: args.maxWithdrawRaw,
      onchainAssetsRaw: args.onchainAssetsBigInt,
    })

  if (liquidityWarning && baseStatus === 'matched') {
    return { status: 'liquidity_warning', ppsUnavailable: false, liquidityWarning: true }
  }

  return { status: baseStatus, ppsUnavailable: false, liquidityWarning }
}

/** Job de réconciliation ledger ↔ on-chain (ERC4626 Ledgity). */
export async function runLedgityVaultReconciliation(): Promise<LedgityReconciliationRunSummary> {
  const startedAt = new Date()
  const configs = await listPublishedPortalLedgityVaultConfigs()
  const pairs = await loadWalletVaultPairs(configs)

  const run = await prisma.ledgityVaultReconciliationRun.create({
    data: { startedAt },
  })

  let matchedCount = 0
  let mismatchCount = 0
  let missingOnchainCount = 0
  let missingLedgerCount = 0
  let ppsUnavailableCount = 0
  let liquidityWarningCount = 0
  const logs: Array<Record<string, unknown>> = []

  for (const pair of pairs) {
    const config = configs.find((row) => normalizeVaultAddress(row.vaultAddress) === pair.vaultAddress)
    if (!config) continue

    const ledgerRows = await prisma.onchainVaultTransaction.findMany({
      where: {
        personId: pair.personId,
        vaultAddress: pair.vaultAddress,
        walletAddress: pair.walletAddress,
        status: 'success',
        operation: { in: ['deposit', 'withdraw'] },
        integrationMode: 'ledgity_vault',
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
      personId: pair.personId,
    })

    const liquidity = await readLedgityWithdrawLiquidity({
      vaultAddress: pair.vaultAddress,
      walletAddress: pair.walletAddress,
      chainId: config.chainId,
    })

    const ledgerAssetsRaw =
      position?.lastAssetsRaw ??
      (ledgerRows.length > 0 ? computePrincipalNetFromLedgerRows(ledgerRows).toString() : '0')
    const onchainAssetsRaw = onchain?.assetsRaw ?? '0'
    const onchainAssetsBigInt = BigInt(onchainAssetsRaw || '0')

    const resolved = resolveReconciliationStatus({
      ledgerAssetsRaw,
      onchainAssetsRaw,
      ppsAtReconcile: onchain?.ppsAtReconcile ?? null,
      maxWithdrawRaw: liquidity?.maxWithdrawRaw ?? null,
      onchainAssetsBigInt,
    })

    const status = resolved.status
    const deltaAssetsRaw = (onchainAssetsBigInt - BigInt(ledgerAssetsRaw || '0')).toString()

    if (status === 'matched') matchedCount += 1
    if (status === 'mismatch') mismatchCount += 1
    if (status === 'missing_onchain') missingOnchainCount += 1
    if (status === 'missing_ledger') missingLedgerCount += 1
    if (status === 'pps_unavailable') ppsUnavailableCount += 1
    if (status === 'liquidity_warning') liquidityWarningCount += 1

    await prisma.ledgityVaultReconciliationItem.create({
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
        ppsAtReconcile: onchain?.ppsAtReconcile ?? null,
        detailsJson: {
          chainId: config.chainId ?? LEDGITY_CHAIN_ID,
          shareSymbol: resolveLedgityShareSymbol(pair.vaultAddress, position?.assetSymbol ?? undefined),
          maxWithdrawRaw: liquidity?.maxWithdrawRaw?.toString() ?? null,
          maxRedeemRaw: liquidity?.maxRedeemRaw?.toString() ?? null,
          previewRedeemRaw: liquidity?.previewRedeemRaw?.toString() ?? null,
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
    }
  }

  const finishedAt = new Date()
  await prisma.ledgityVaultReconciliationRun.update({
    where: { id: run.id },
    data: {
      finishedAt,
      itemsChecked: pairs.length,
      matchedCount,
      mismatchCount,
      missingOnchainCount,
      missingLedgerCount,
      ppsUnavailableCount,
      liquidityWarningCount,
      logJson: logs as Prisma.InputJsonValue,
    },
  })

  return {
    runId: run.id,
    itemsChecked: pairs.length,
    matchedCount,
    mismatchCount,
    missingOnchainCount,
    missingLedgerCount,
    ppsUnavailableCount,
    liquidityWarningCount,
    startedAt: startedAt.toISOString(),
    finishedAt: finishedAt.toISOString(),
  }
}

export async function getLatestLedgityReconciliationRun() {
  return prisma.ledgityVaultReconciliationRun.findFirst({
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

export async function getLedgityMonitoringSnapshot(args?: { pendingMinutes?: number }) {
  const pendingMinutes = args?.pendingMinutes ?? getLedgityPendingAlertMinutes()
  const pendingCutoff = new Date(Date.now() - pendingMinutes * 60_000)

  const [publishedConfigs, pendingTxs, failedTxs, positions, latestRun, dependencyHealth] = await Promise.all([
    listPublishedPortalLedgityVaultConfigs(),
    prisma.onchainVaultTransaction.findMany({
      where: {
        status: 'pending',
        integrationMode: 'ledgity_vault',
        createdAt: { lte: pendingCutoff },
      },
      orderBy: { createdAt: 'asc' },
      take: 100,
    }),
    prisma.onchainVaultTransaction.findMany({
      where: {
        status: { in: ['failed', 'reverted'] },
        integrationMode: 'ledgity_vault',
      },
      orderBy: { createdAt: 'desc' },
      take: 50,
    }),
    prisma.userVaultPosition.findMany({
      where: {
        vaultAddress: {
          in: (await listPublishedPortalLedgityVaultConfigs()).map((row) => normalizeVaultAddress(row.vaultAddress)),
        },
      },
      select: {
        vaultAddress: true,
        lastAssetsRaw: true,
        assetSymbol: true,
        costBasisUnknown: true,
      },
    }),
    getLatestLedgityReconciliationRun(),
    checkLedgityDependencyHealth(),
  ])

  const assetsByVault = new Map<string, bigint>()
  let costBasisUnknownCount = 0
  for (const row of positions) {
    const current = assetsByVault.get(row.vaultAddress) ?? BigInt(0)
    assetsByVault.set(row.vaultAddress, current + BigInt(row.lastAssetsRaw || '0'))
    if (row.costBasisUnknown) costBasisUnknownCount += 1
  }

  const mismatches = latestRun?.items ?? []
  const significantMismatchCount = mismatches.filter(
    (row) => row.status === 'mismatch' && isSignificantLedgityMismatchDelta(row.deltaAssetsRaw),
  ).length

  const vaultRows = await Promise.all(
    publishedConfigs.map(async (config) => {
      const vaultAddress = normalizeVaultAddress(config.vaultAddress)
      const trackedAssetsRaw = assetsByVault.get(vaultAddress) ?? BigInt(0)
      const metrics = await readLedgityVaultLiquidityMetrics({ vaultAddress, chainId: config.chainId })

      const catalogRows = isLedgityLocalSandboxEnabled()
        ? []
        : await fetchLedgityVaultCatalog({ addresses: [vaultAddress], chainId: config.chainId })

      const catalog = catalogRows[0]
      const liquidityLow =
        metrics != null &&
        isLedgityVaultLiquidityLow({
          totalAssetsRaw: metrics.totalAssetsRaw,
          trackedLedgerAssetsRaw: trackedAssetsRaw,
        })

      const withdrawAvailability =
        metrics?.paused === true
          ? 'paused'
          : liquidityLow
            ? 'deferred'
            : metrics?.pricePerShare != null
              ? 'instant'
              : 'unknown'

      return {
        vaultAddress,
        label: config.label,
        assetSymbol: catalog?.asset.symbol ?? 'USDC',
        shareSymbol: resolveLedgityShareSymbol(vaultAddress, catalog?.asset.symbol),
        integrationMode: config.integrationMode,
        netApy: catalog?.netApy ?? null,
        pricePerShare: metrics?.pricePerShare ?? catalog?.pricePerShare ?? null,
        tvlUsd: catalog?.tvlUsd ?? null,
        liquidityBufferRaw: metrics?.totalAssetsRaw.toString() ?? null,
        liquidityLow,
        withdrawAvailability,
        paused: metrics?.paused ?? null,
        trackedAssetsRaw: trackedAssetsRaw.toString(),
      }
    }),
  )

  const vaultPausedCount = vaultRows.filter((row) => row.paused === true).length
  const withdrawalsPausedCount = vaultPausedCount
  const vaultLiquidityLowCount = vaultRows.filter((row) => row.liquidityLow).length

  const alerts = buildLedgityMonitoringAlerts({
    pendingTransactionsCount: pendingTxs.length,
    pendingThresholdMinutes: pendingMinutes,
    mismatchCount: latestRun?.mismatchCount ?? 0,
    significantMismatchCount,
    missingOnchainCount: latestRun?.missingOnchainCount ?? 0,
    missingLedgerCount: latestRun?.missingLedgerCount ?? 0,
    ppsUnavailableCount: latestRun?.ppsUnavailableCount ?? 0,
    liquidityWarningCount: (latestRun?.liquidityWarningCount ?? 0) + vaultLiquidityLowCount,
    vaultPausedCount,
    withdrawalsPausedCount,
    dependencyHealth,
    sandboxEnabledInProd: isLedgitySandboxEnabledInProduction(),
  })

  const globalStatus = computeLedgityGlobalStatus(alerts)
  const beta = formatLedgityBetaDashboardForClient(
    await getLedgityBetaDashboardStats({
      mismatchCount: latestRun?.mismatchCount ?? 0,
      pendingTxCount: pendingTxs.length,
    }),
  )

  return {
    globalStatus,
    alerts,
    dependencyHealth,
    runtimeMode: getLedgityRuntimeModeSnapshot(),
    beta,
    activeVaults: vaultRows,
    pendingTransactions: pendingTxs.map((row) => ({
      id: row.id,
      personId: row.personId,
      vaultAddress: row.vaultAddress,
      operation: row.operation,
      integrationMode: row.integrationMode,
      createdAt: row.createdAt.toISOString(),
      idempotencyKey: row.idempotencyKey,
    })),
    failedTransactions: failedTxs.map((row) => ({
      id: row.id,
      personId: row.personId,
      vaultAddress: row.vaultAddress,
      operation: row.operation,
      status: row.status,
      errorMessage: row.errorMessage,
      createdAt: row.createdAt.toISOString(),
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
          ppsUnavailableCount: latestRun.ppsUnavailableCount,
          liquidityWarningCount: latestRun.liquidityWarningCount,
          mismatches: latestRun.items,
        }
      : null,
  }
}
