import { prisma } from '@/lib/prisma'
import { fetchMorphoVaultPosition, fetchMorphoVaultsByAddresses } from '@/lib/portal/morphoGraphql'
import { isMorphoLocalSandboxEnabled } from '@/lib/portal/morphoLocalSandboxConfig'
import { fetchSandboxMorphoVaultPosition } from '@/lib/portal/mocks/morphoLocalSandbox'
import { MORPHO_CHAIN_ID, normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import { resolvePortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'
import {
  formatEarnTokenAmount,
  mapMorphoVaultPosition,
  mergeMorphoVaultConfigWithGraphql,
} from '@/lib/portal/morphoVaultFormat'
import type { MorphoVaultPositionRow } from '@/lib/portal/morphoGraphql'
import { loadPrincipalNetRaw } from '@/lib/portal/morphoVaultLedger'
import type {
  PortalSavingsPosition,
  PortalSavingsSummary,
  PortalSavingsVaultDetailPayload,
  PortalSavingsVaultTransaction,
} from '@/lib/portal/portalSavingsTypes'
import type { PortalMorphoVaultDetails } from '@/lib/portal/morphoVaultTypes'
import { getMorphoBetaPortalFlags } from '@/lib/portal/morphoUsdcBetaAccess'
import { isExternalWalletVerified } from '@/lib/wallet/externalWalletVerification'

const STABLECOIN_USD_TO_EUR = 0.92

type VaultAggregate = {
  vaultAddress: string
  vaultName: string
  provider: string
  userApyBps: number | null
  assetSymbol: string
  assetDecimals: number
  assetsRaw: bigint
  assetsUsd: number
  earnedYieldParts: string[]
  yieldSyncPending: boolean
}

function resolvePositionUsd(row: MorphoVaultPositionRow): number {
  if (row.assetsUsd != null && Number.isFinite(row.assetsUsd)) return row.assetsUsd
  const human = Number(formatEarnTokenAmount(row.assets, row.asset.decimals))
  return Number.isFinite(human) ? human : 0
}

function toSummaryValues(totalUsd: number): Pick<NonNullable<PortalSavingsSummary>, 'total_value_eur' | 'total_value_usd'> {
  return {
    total_value_usd: totalUsd,
    total_value_eur: totalUsd * STABLECOIN_USD_TO_EUR,
  }
}

async function loadPersonEvmWalletAddresses(personId: string): Promise<string[]> {
  const rows = await prisma.personCryptoWallet.findMany({
    where: { personId, revokedAt: null, chainType: 'evm' },
    select: { address: true, provider: true, metadataJson: true },
  })

  return rows
    .filter((row) => row.provider !== 'external' || isExternalWalletVerified(row.metadataJson))
    .map((row) => row.address.trim().toLowerCase())
}

function emptySummary(): PortalSavingsSummary {
  return {
    positions_count: 0,
    positions: [],
    total_value_eur: 0,
    total_value_usd: 0,
  }
}

function buildPositionRow(aggregate: VaultAggregate): PortalSavingsPosition {
  const estimatedValueUsd = aggregate.assetsUsd
  const estimatedValueEur = estimatedValueUsd * STABLECOIN_USD_TO_EUR
  const earnedYieldDisplay =
    aggregate.earnedYieldParts.length === 1
      ? aggregate.earnedYieldParts[0]!
      : aggregate.earnedYieldParts.length > 1
        ? `${aggregate.earnedYieldParts.length} wallets · rendement agrégé`
        : '—'

  return {
    vaultAddress: aggregate.vaultAddress,
    vaultName: aggregate.vaultName,
    assetSymbol: aggregate.assetSymbol,
    assetsInVaultDisplay: `${formatEarnTokenAmount(aggregate.assetsRaw.toString(), aggregate.assetDecimals)} ${aggregate.assetSymbol}`,
    assetsUsd: estimatedValueUsd,
    estimatedValueUsd,
    estimatedValueEur,
    earnedYieldDisplay,
    yieldSyncStatus: aggregate.yieldSyncPending ? 'pending' : 'synced',
    userApyBps: aggregate.userApyBps,
    provider: aggregate.provider,
  }
}

async function loadLedgerBackedRows(personId: string): Promise<PortalSavingsSummary> {
  const configs = await resolvePortalMorphoVaultConfigs({ publishedOnly: true })
  if (configs.length === 0) return emptySummary()

  const vaultAddresses = configs.map((config) => normalizeVaultAddress(config.vaultAddress))
  const configByVault = new Map(
    configs.map((config) => [normalizeVaultAddress(config.vaultAddress), config]),
  )

  const storedRows = await prisma.userVaultPosition.findMany({
    where: {
      personId,
      vaultAddress: { in: vaultAddresses },
    },
    select: {
      vaultAddress: true,
      lastAssetsRaw: true,
      assetSymbol: true,
      assetDecimals: true,
    },
  })

  const aggregates = new Map<string, VaultAggregate>()

  for (const row of storedRows) {
    const assetsRaw = BigInt(row.lastAssetsRaw || '0')
    if (assetsRaw <= BigInt(0)) continue

    const vaultAddress = normalizeVaultAddress(row.vaultAddress)
    const config = configByVault.get(vaultAddress)
    if (!config) continue

    const usd = Number(formatEarnTokenAmount(row.lastAssetsRaw ?? '0', row.assetDecimals))
    const vaultName = config.label?.trim() || 'Vault Morpho'
    const existing = aggregates.get(vaultAddress)

    if (existing) {
      existing.assetsRaw += assetsRaw
      existing.assetsUsd += Number.isFinite(usd) ? usd : 0
      continue
    }

    aggregates.set(vaultAddress, {
      vaultAddress,
      vaultName,
      provider: 'morpho',
      userApyBps: null,
      assetSymbol: row.assetSymbol,
      assetDecimals: row.assetDecimals,
      assetsRaw,
      assetsUsd: Number.isFinite(usd) ? usd : 0,
      earnedYieldParts: [],
      yieldSyncPending: true,
    })
  }

  const gqlCatalog = await fetchMorphoVaultsByAddresses({ addresses: vaultAddresses }).catch(() => [])
  for (const aggregate of aggregates.values()) {
    const config = configByVault.get(aggregate.vaultAddress)
    if (!config) continue
    const gql = gqlCatalog.find((item) => normalizeVaultAddress(item.address) === aggregate.vaultAddress)
    const details = mergeMorphoVaultConfigWithGraphql(config, gql ?? null)
    aggregate.vaultName = details.name
    aggregate.userApyBps = details.userApyBps
    aggregate.provider = details.provider
  }

  const positions = [...aggregates.values()].map(buildPositionRow)
  const totalUsd = positions.reduce((sum, position) => sum + (position.estimatedValueUsd ?? 0), 0)

  return {
    positions_count: positions.length,
    positions,
    ...toSummaryValues(totalUsd),
  }
}

async function loadLiveRows(personId: string): Promise<{ summary: PortalSavingsSummary; partial: boolean }> {
  const configs = await resolvePortalMorphoVaultConfigs({ publishedOnly: true })
  if (configs.length === 0) return { summary: emptySummary(), partial: false }

  const wallets = await loadPersonEvmWalletAddresses(personId)
  if (wallets.length === 0) return { summary: emptySummary(), partial: false }

  const vaultAddresses = configs.map((config) => normalizeVaultAddress(config.vaultAddress))
  const gqlCatalog = await fetchMorphoVaultsByAddresses({ addresses: vaultAddresses }).catch(() => [])
  const gqlByVault = new Map(gqlCatalog.map((item) => [normalizeVaultAddress(item.address), item]))

  const aggregates = new Map<string, VaultAggregate>()
  let partial = gqlCatalog.length === 0

  const combos = configs.flatMap((config) =>
    wallets.map((walletAddress) => ({
      config,
      vaultAddress: normalizeVaultAddress(config.vaultAddress),
      walletAddress,
    })),
  )

  await Promise.all(
    combos.map(async ({ config, vaultAddress, walletAddress }) => {
      try {
        const row = isMorphoLocalSandboxEnabled()
          ? await fetchSandboxMorphoVaultPosition({ personId, vaultAddress, walletAddress })
          : await fetchMorphoVaultPosition({
              vaultAddress,
              walletAddress,
              chainId: config.chainId ?? MORPHO_CHAIN_ID,
            })

        if (!row || BigInt(row.assets || '0') <= BigInt(0)) return

        const principalNetRaw = await loadPrincipalNetRaw({
          personId,
          vaultAddress,
          chainId: config.chainId ?? MORPHO_CHAIN_ID,
          walletAddress,
        }).catch(() => null)

        const mapped = mapMorphoVaultPosition(row, vaultAddress, {
          principalNetRaw,
          costBasisUnknown: principalNetRaw == null,
        })

        const gql = gqlByVault.get(vaultAddress) ?? null
        const details = mergeMorphoVaultConfigWithGraphql(config, gql)
        const usd = resolvePositionUsd(row)
        const existing = aggregates.get(vaultAddress)

        if (existing) {
          existing.assetsRaw += BigInt(row.assets)
          existing.assetsUsd += usd
          existing.earnedYieldParts.push(mapped.earnedYieldDisplay)
          if (mapped.yieldSyncStatus === 'pending') existing.yieldSyncPending = true
          return
        }

        aggregates.set(vaultAddress, {
          vaultAddress,
          vaultName: details.name,
          provider: details.provider,
          userApyBps: details.userApyBps,
          assetSymbol: row.asset.symbol,
          assetDecimals: row.asset.decimals,
          assetsRaw: BigInt(row.assets),
          assetsUsd: usd,
          earnedYieldParts: [mapped.earnedYieldDisplay],
          yieldSyncPending: mapped.yieldSyncStatus === 'pending',
        })
      } catch {
        partial = true
      }
    }),
  )

  const positions = [...aggregates.values()].map(buildPositionRow)
  const totalUsd = positions.reduce((sum, position) => sum + (position.estimatedValueUsd ?? 0), 0)

  return {
    summary: {
      positions_count: positions.length,
      positions,
      ...toSummaryValues(totalUsd),
    },
    partial,
  }
}

/** Positions épargne DeFi — ledger (dashboard) ou on-chain (hub épargne). */
export async function loadPortalSavingsSummary(args: {
  personId: string
  live?: boolean
}): Promise<{ savings: PortalSavingsSummary; partial: boolean }> {
  if (args.live) {
    const live = await loadLiveRows(args.personId)
    return { savings: live.summary, partial: live.partial }
  }

  const savings = await loadLedgerBackedRows(args.personId)
  return { savings, partial: false }
}

type LedgerTransactionRow = {
  id: string
  vaultAddress: string
  walletAddress: string
  operation: string
  amountRaw: string
  assetSymbol: string
  assetDecimals: number
  status: string
  txHash: string | null
  createdAt: Date
}

async function loadVaultLedgerTransactions(args: {
  personId: string
  vaultAddress: string
  limit?: number
}): Promise<LedgerTransactionRow[]> {
  return prisma.onchainVaultTransaction.findMany({
    where: {
      personId: args.personId,
      vaultAddress: args.vaultAddress.toLowerCase(),
      operation: { in: ['deposit', 'withdraw'] },
    },
    orderBy: { createdAt: 'desc' },
    take: args.limit ?? 50,
    select: {
      id: true,
      vaultAddress: true,
      walletAddress: true,
      operation: true,
      amountRaw: true,
      assetSymbol: true,
      assetDecimals: true,
      status: true,
      txHash: true,
      createdAt: true,
    },
  })
}

async function loadSingleVaultLiveAggregate(args: {
  personId: string
  vaultAddress: string
}): Promise<{ aggregate: VaultAggregate | null; vaultDetails: PortalMorphoVaultDetails | null; partial: boolean }> {
  const normalizedVault = normalizeVaultAddress(args.vaultAddress)
  const configs = await resolvePortalMorphoVaultConfigs({ publishedOnly: true })
  const config = configs.find((row) => normalizeVaultAddress(row.vaultAddress) === normalizedVault)
  if (!config) {
    return { aggregate: null, vaultDetails: null, partial: false }
  }

  const wallets = await loadPersonEvmWalletAddresses(args.personId)
  if (wallets.length === 0) {
    const gqlCatalog = await fetchMorphoVaultsByAddresses({ addresses: [normalizedVault] }).catch(() => [])
    const gql = gqlCatalog[0] ?? null
    return {
      aggregate: null,
      vaultDetails: mergeMorphoVaultConfigWithGraphql(config, gql),
      partial: gqlCatalog.length === 0,
    }
  }

  const gqlCatalog = await fetchMorphoVaultsByAddresses({ addresses: [normalizedVault] }).catch(() => [])
  const gql = gqlCatalog[0] ?? null
  const vaultDetails = mergeMorphoVaultConfigWithGraphql(config, gql)
  let partial = gqlCatalog.length === 0
  let aggregate: VaultAggregate | null = null

  await Promise.all(
    wallets.map(async (walletAddress) => {
      try {
        const row = isMorphoLocalSandboxEnabled()
          ? await fetchSandboxMorphoVaultPosition({
              personId: args.personId,
              vaultAddress: normalizedVault,
              walletAddress,
            })
          : await fetchMorphoVaultPosition({
              vaultAddress: normalizedVault,
              walletAddress,
              chainId: config.chainId ?? MORPHO_CHAIN_ID,
            })

        if (!row || BigInt(row.assets || '0') <= BigInt(0)) return

        const principalNetRaw = await loadPrincipalNetRaw({
          personId: args.personId,
          vaultAddress: normalizedVault,
          chainId: config.chainId ?? MORPHO_CHAIN_ID,
          walletAddress,
        }).catch(() => null)

        const mapped = mapMorphoVaultPosition(row, normalizedVault, {
          principalNetRaw,
          costBasisUnknown: principalNetRaw == null,
        })

        const usd = resolvePositionUsd(row)
        if (aggregate) {
          aggregate.assetsRaw += BigInt(row.assets)
          aggregate.assetsUsd += usd
          aggregate.earnedYieldParts.push(mapped.earnedYieldDisplay)
          if (mapped.yieldSyncStatus === 'pending') aggregate.yieldSyncPending = true
          return
        }

        aggregate = {
          vaultAddress: normalizedVault,
          vaultName: vaultDetails.name,
          provider: vaultDetails.provider,
          userApyBps: vaultDetails.userApyBps,
          assetSymbol: row.asset.symbol,
          assetDecimals: row.asset.decimals,
          assetsRaw: BigInt(row.assets),
          assetsUsd: usd,
          earnedYieldParts: [mapped.earnedYieldDisplay],
          yieldSyncPending: mapped.yieldSyncStatus === 'pending',
        }
      } catch {
        partial = true
      }
    }),
  )

  return { aggregate, vaultDetails, partial }
}

/** Détail d’un vault épargne — position live, historique ledger, APY. */
export async function loadPortalSavingsVaultDetail(args: {
  personId: string
  vaultAddress: string
  currency: string
  mapTransactions: (
    rows: LedgerTransactionRow[],
    currentBalanceUsd: number,
  ) => {
    transactions: PortalSavingsVaultTransaction[]
    historyPoints: number[]
  }
}): Promise<PortalSavingsVaultDetailPayload | null> {
  const normalizedVault = normalizeVaultAddress(args.vaultAddress)
  const { aggregate, vaultDetails, partial: livePartial } = await loadSingleVaultLiveAggregate({
    personId: args.personId,
    vaultAddress: normalizedVault,
  })

  if (!vaultDetails) return null

  const position = aggregate
    ? buildPositionRow(aggregate)
    : {
        vaultAddress: normalizedVault,
        vaultName: vaultDetails.name,
        assetSymbol: vaultDetails.asset.symbol,
        assetsInVaultDisplay: `0 ${vaultDetails.asset.symbol}`,
        assetsUsd: 0,
        estimatedValueUsd: 0,
        estimatedValueEur: 0,
        earnedYieldDisplay: '—',
        yieldSyncStatus: 'pending' as const,
        userApyBps: vaultDetails.userApyBps,
        provider: vaultDetails.provider,
      }

  const ledgerRows = await loadVaultLedgerTransactions({
    personId: args.personId,
    vaultAddress: normalizedVault,
  })
  const { transactions, historyPoints } = args.mapTransactions(
    ledgerRows,
    position.estimatedValueUsd ?? position.assetsUsd ?? 0,
  )

  const beta = await getMorphoBetaPortalFlags(args.personId)
  const averageApyBps = vaultDetails.userApyBps ?? position.userApyBps

  return {
    currency: args.currency,
    vaultAddress: normalizedVault,
    vaultName: vaultDetails.name,
    assetSymbol: vaultDetails.asset.symbol,
    position,
    averageApyBps,
    averageApyDisplay:
      averageApyBps != null && Number.isFinite(averageApyBps)
        ? `${(averageApyBps / 100).toFixed(2)}%`
        : '—',
    historyPoints,
    transactions,
    vault: vaultDetails,
    beta,
    partial: livePartial,
  }
}
