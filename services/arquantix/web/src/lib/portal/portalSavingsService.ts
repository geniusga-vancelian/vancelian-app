import type { PortalMorphoVaultConfig } from '@prisma/client'

import { fetchLedgityVaultCatalog, fetchLedgityVaultPosition } from '@/lib/portal/ledgity/ledgityVaultAdapter'
import { getLedgityBetaPortalFlags } from '@/lib/portal/ledgity/ledgityBetaAccess'
import { LEDGITY_CHAIN_ID, normalizeVaultAddress as normalizeLedgityVaultAddress } from '@/lib/portal/ledgity/ledgityConstants'
import { isLedgityLocalSandboxEnabled } from '@/lib/portal/ledgity/ledgityLocalSandboxConfig'
import { resolvePortalLedgityVaultConfigs } from '@/lib/portal/ledgity/ledgityVaultConfigStore'
import {
  mapLedgityVaultPosition,
  mergeLedgityVaultConfigWithCatalog,
} from '@/lib/portal/ledgity/ledgityVaultFormat'
import { fetchSandboxLedgityVaultPosition } from '@/lib/portal/ledgity/mocks/ledgityLocalSandbox'
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
import { getMorphoBetaPortalFlags } from '@/lib/portal/morphoUsdcBetaAccess'
import {
  resolveSavingsDisplayCurrency,
  resolveSavingsPositionValue,
  resolveStablecoinValuations,
  SAVINGS_STABLECOIN_USD_TO_EUR,
} from '@/lib/portal/portalSavingsFormat'
import type {
  PortalDefiIntegrationMode,
  PortalDefiVaultDetails,
  PortalSavingsPosition,
  PortalSavingsSummary,
  PortalSavingsVaultDetailPayload,
  PortalSavingsVaultTransaction,
} from '@/lib/portal/portalSavingsTypes'
import { isExternalWalletVerified } from '@/lib/wallet/externalWalletVerification'

type VaultAggregate = {
  vaultAddress: string
  vaultName: string
  provider: string
  integrationMode: PortalDefiIntegrationMode
  userApyBps: number | null
  assetSymbol: string
  assetDecimals: number
  assetsRaw: bigint
  assetsUsd: number
  earnedYieldParts: string[]
  yieldSyncPending: boolean
}

type PositionFetchRow = {
  assets: string
  asset: { address?: string; symbol: string; decimals: number }
  assetsUsd?: number | null
}

export async function resolveAllPublishedDefiVaultConfigs(): Promise<PortalMorphoVaultConfig[]> {
  const [morpho, ledgity] = await Promise.all([
    resolvePortalMorphoVaultConfigs({ publishedOnly: true }),
    resolvePortalLedgityVaultConfigs({ publishedOnly: true }),
  ])
  return [...morpho, ...ledgity].sort((a, b) => a.sortOrder - b.sortOrder || a.createdAt.getTime() - b.createdAt.getTime())
}

function isLedgityConfig(config: PortalMorphoVaultConfig): boolean {
  return (config.integrationMode as string) === 'ledgity_vault'
}

function resolvePositionUsd(row: PositionFetchRow): number {
  if (row.assetsUsd != null && Number.isFinite(row.assetsUsd)) return row.assetsUsd
  const human = Number(formatEarnTokenAmount(row.assets, row.asset.decimals))
  return Number.isFinite(human) ? human : 0
}

function toSummaryValues(
  totalEur: number,
  totalUsd: number,
): Pick<NonNullable<PortalSavingsSummary>, 'total_value_eur' | 'total_value_usd'> {
  return {
    total_value_eur: totalEur,
    total_value_usd: totalUsd,
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
  const humanAmount = Number(
    formatEarnTokenAmount(aggregate.assetsRaw.toString(), aggregate.assetDecimals),
  )
  const valuations = resolveStablecoinValuations(
    aggregate.assetSymbol,
    Number.isFinite(humanAmount) ? humanAmount : aggregate.assetsUsd,
    SAVINGS_STABLECOIN_USD_TO_EUR,
  )
  const estimatedValueUsd = valuations.estimatedValueUsd
  const estimatedValueEur = valuations.estimatedValueEur
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
    integrationMode: aggregate.integrationMode,
  }
}

async function fetchDefiVaultPosition(args: {
  personId: string
  config: PortalMorphoVaultConfig
  vaultAddress: string
  walletAddress: string
}): Promise<PositionFetchRow | null> {
  if (isLedgityConfig(args.config)) {
    const row = isLedgityLocalSandboxEnabled()
      ? await fetchSandboxLedgityVaultPosition({
          personId: args.personId,
          vaultAddress: args.vaultAddress,
          walletAddress: args.walletAddress,
        })
      : await fetchLedgityVaultPosition({
          vaultAddress: args.vaultAddress,
          walletAddress: args.walletAddress,
          chainId: args.config.chainId ?? LEDGITY_CHAIN_ID,
        })
    return row
  }

  const row: MorphoVaultPositionRow | null = isMorphoLocalSandboxEnabled()
    ? await fetchSandboxMorphoVaultPosition({
        personId: args.personId,
        vaultAddress: args.vaultAddress,
        walletAddress: args.walletAddress,
      })
    : await fetchMorphoVaultPosition({
        vaultAddress: args.vaultAddress,
        walletAddress: args.walletAddress,
        chainId: args.config.chainId ?? MORPHO_CHAIN_ID,
      })
  return row
}

function mapDefiVaultPosition(args: {
  config: PortalMorphoVaultConfig
  row: PositionFetchRow
  vaultAddress: string
  principalNetRaw: string | null
}): { earnedYieldDisplay: string; yieldSyncStatus?: 'synced' | 'pending' } {
  if (isLedgityConfig(args.config)) {
    const mapped = mapLedgityVaultPosition(
      {
        assets: args.row.assets,
        shares: '0',
        assetsUsd: args.row.assetsUsd ?? null,
        asset: {
          address: args.row.asset.address ?? '',
          symbol: args.row.asset.symbol,
          decimals: args.row.asset.decimals,
        },
      },
      args.vaultAddress,
      {
        principalNetRaw: args.principalNetRaw,
        costBasisUnknown: args.principalNetRaw == null,
      },
    )
    return {
      earnedYieldDisplay: mapped.earnedYieldDisplay,
      yieldSyncStatus: mapped.yieldSyncStatus,
    }
  }

  const mapped = mapMorphoVaultPosition(
    args.row as MorphoVaultPositionRow,
    args.vaultAddress,
    {
      principalNetRaw: args.principalNetRaw,
      costBasisUnknown: args.principalNetRaw == null,
    },
  )
  return {
    earnedYieldDisplay: mapped.earnedYieldDisplay,
    yieldSyncStatus: mapped.yieldSyncStatus,
  }
}

async function mergeVaultDetails(
  config: PortalMorphoVaultConfig,
  vaultAddress: string,
  morphoCatalogByVault: Map<string, Awaited<ReturnType<typeof fetchMorphoVaultsByAddresses>>[number]>,
  ledgityCatalogByVault: Map<string, Awaited<ReturnType<typeof fetchLedgityVaultCatalog>>[number]>,
): Promise<PortalDefiVaultDetails> {
  if (isLedgityConfig(config)) {
    return mergeLedgityVaultConfigWithCatalog(
      config,
      ledgityCatalogByVault.get(vaultAddress) ?? null,
    )
  }
  return mergeMorphoVaultConfigWithGraphql(config, morphoCatalogByVault.get(vaultAddress) ?? null)
}

async function loadLedgerBackedRows(
  personId: string,
  walletAddress?: string,
): Promise<PortalSavingsSummary> {
  const configs = await resolveAllPublishedDefiVaultConfigs()
  if (configs.length === 0) return emptySummary()

  const vaultAddresses = configs.map((config) => normalizeVaultAddress(config.vaultAddress))
  const configByVault = new Map(
    configs.map((config) => [normalizeVaultAddress(config.vaultAddress), config]),
  )

  const storedRows = await prisma.userVaultPosition.findMany({
    where: {
      personId,
      vaultAddress: { in: vaultAddresses },
      ...(walletAddress ? { walletAddress: walletAddress.toLowerCase() } : {}),
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
    const vaultName = config.label?.trim() || (isLedgityConfig(config) ? 'Vault Ledgity' : 'Vault Morpho')
    const existing = aggregates.get(vaultAddress)

    if (existing) {
      existing.assetsRaw += assetsRaw
      existing.assetsUsd += Number.isFinite(usd) ? usd : 0
      continue
    }

    aggregates.set(vaultAddress, {
      vaultAddress,
      vaultName,
      provider: isLedgityConfig(config) ? 'ledgity' : 'morpho',
      integrationMode: isLedgityConfig(config) ? 'ledgity_vault' : 'direct_morpho',
      userApyBps: null,
      assetSymbol: row.assetSymbol,
      assetDecimals: row.assetDecimals,
      assetsRaw,
      assetsUsd: Number.isFinite(usd) ? usd : 0,
      earnedYieldParts: [],
      yieldSyncPending: true,
    })
  }

  const morphoAddresses = configs.filter((c) => !isLedgityConfig(c)).map((c) => normalizeVaultAddress(c.vaultAddress))
  const ledgityAddresses = configs.filter(isLedgityConfig).map((c) => normalizeLedgityVaultAddress(c.vaultAddress))

  const [morphoCatalog, ledgityCatalog] = await Promise.all([
    morphoAddresses.length ? fetchMorphoVaultsByAddresses({ addresses: morphoAddresses }).catch(() => []) : [],
    ledgityAddresses.length ? fetchLedgityVaultCatalog({ addresses: ledgityAddresses }).catch(() => []) : [],
  ])

  const morphoByVault = new Map(morphoCatalog.map((item) => [normalizeVaultAddress(item.address), item]))
  const ledgityByVault = new Map(ledgityCatalog.map((item) => [normalizeLedgityVaultAddress(item.address), item]))

  for (const aggregate of aggregates.values()) {
    const config = configByVault.get(aggregate.vaultAddress)
    if (!config) continue
    const details = await mergeVaultDetails(config, aggregate.vaultAddress, morphoByVault, ledgityByVault)
    aggregate.vaultName = details.name
    aggregate.userApyBps = details.userApyBps
    aggregate.provider = details.provider
    aggregate.integrationMode = isLedgityConfig(config) ? 'ledgity_vault' : 'direct_morpho'
  }

  const positions = [...aggregates.values()].map(buildPositionRow)
  const totalUsd = positions.reduce((sum, position) => sum + (position.estimatedValueUsd ?? 0), 0)
  const totalEur = positions.reduce((sum, position) => sum + (position.estimatedValueEur ?? 0), 0)

  return {
    positions_count: positions.length,
    positions,
    ...toSummaryValues(totalEur, totalUsd),
  }
}

async function loadLiveRows(
  personId: string,
  walletAddress?: string,
): Promise<{ summary: PortalSavingsSummary; partial: boolean }> {
  const configs = await resolveAllPublishedDefiVaultConfigs()
  if (configs.length === 0) return { summary: emptySummary(), partial: false }

  const wallets = walletAddress
    ? [walletAddress.toLowerCase()]
    : await loadPersonEvmWalletAddresses(personId)
  if (wallets.length === 0) return { summary: emptySummary(), partial: false }

  const morphoAddresses = configs.filter((c) => !isLedgityConfig(c)).map((c) => normalizeVaultAddress(c.vaultAddress))
  const ledgityAddresses = configs.filter(isLedgityConfig).map((c) => normalizeLedgityVaultAddress(c.vaultAddress))

  const [morphoCatalog, ledgityCatalog] = await Promise.all([
    morphoAddresses.length ? fetchMorphoVaultsByAddresses({ addresses: morphoAddresses }).catch(() => []) : [],
    ledgityAddresses.length ? fetchLedgityVaultCatalog({ addresses: ledgityAddresses }).catch(() => []) : [],
  ])

  const morphoByVault = new Map(morphoCatalog.map((item) => [normalizeVaultAddress(item.address), item]))
  const ledgityByVault = new Map(ledgityCatalog.map((item) => [normalizeLedgityVaultAddress(item.address), item]))

  const aggregates = new Map<string, VaultAggregate>()
  let partial = morphoCatalog.length === 0 && ledgityCatalog.length === 0 && configs.length > 0

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
        const row = await fetchDefiVaultPosition({ personId, config, vaultAddress, walletAddress })

        if (!row || BigInt(row.assets || '0') <= BigInt(0)) return

        const chainId = isLedgityConfig(config) ? LEDGITY_CHAIN_ID : (config.chainId ?? MORPHO_CHAIN_ID)
        const principalNetRaw = await loadPrincipalNetRaw({
          personId,
          vaultAddress,
          chainId,
          walletAddress,
        }).catch(() => null)

        const mapped = mapDefiVaultPosition({
          config,
          row,
          vaultAddress,
          principalNetRaw,
        })

        const details = await mergeVaultDetails(config, vaultAddress, morphoByVault, ledgityByVault)
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
          integrationMode: isLedgityConfig(config) ? 'ledgity_vault' : 'direct_morpho',
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
  const totalEur = positions.reduce((sum, position) => sum + (position.estimatedValueEur ?? 0), 0)

  return {
    summary: {
      positions_count: positions.length,
      positions,
      ...toSummaryValues(totalEur, totalUsd),
    },
    partial,
  }
}

/** Positions épargne DeFi — ledger (dashboard) ou on-chain (hub épargne). */
export async function loadPortalSavingsSummary(args: {
  personId: string
  live?: boolean
  walletAddress?: string | null
}): Promise<{ savings: PortalSavingsSummary; partial: boolean }> {
  const walletAddress = args.walletAddress?.trim().toLowerCase() || undefined

  if (args.live) {
    const live = await loadLiveRows(args.personId, walletAddress)
    return { savings: live.summary, partial: live.partial }
  }

  const savings = await loadLedgerBackedRows(args.personId, walletAddress)
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
  walletAddress?: string
  limit?: number
}): Promise<LedgerTransactionRow[]> {
  return prisma.onchainVaultTransaction.findMany({
    where: {
      personId: args.personId,
      vaultAddress: args.vaultAddress.toLowerCase(),
      operation: { in: ['deposit', 'withdraw'] },
      ...(args.walletAddress ? { walletAddress: args.walletAddress.toLowerCase() } : {}),
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
  walletAddress?: string
}): Promise<{ aggregate: VaultAggregate | null; vaultDetails: PortalDefiVaultDetails | null; partial: boolean }> {
  const normalizedVault = normalizeVaultAddress(args.vaultAddress)
  const configs = await resolveAllPublishedDefiVaultConfigs()
  const config = configs.find((row) => normalizeVaultAddress(row.vaultAddress) === normalizedVault)
  if (!config) {
    return { aggregate: null, vaultDetails: null, partial: false }
  }

  const morphoAddresses = isLedgityConfig(config) ? [] : [normalizedVault]
  const ledgityAddresses = isLedgityConfig(config) ? [normalizedVault] : []

  const [morphoCatalog, ledgityCatalog] = await Promise.all([
    morphoAddresses.length ? fetchMorphoVaultsByAddresses({ addresses: morphoAddresses }).catch(() => []) : [],
    ledgityAddresses.length ? fetchLedgityVaultCatalog({ addresses: ledgityAddresses }).catch(() => []) : [],
  ])

  const morphoByVault = new Map(morphoCatalog.map((item) => [normalizeVaultAddress(item.address), item]))
  const ledgityByVault = new Map(ledgityCatalog.map((item) => [normalizeLedgityVaultAddress(item.address), item]))
  const vaultDetails = await mergeVaultDetails(config, normalizedVault, morphoByVault, ledgityByVault)

  const scopedWallet = args.walletAddress?.trim().toLowerCase()
  const wallets = scopedWallet
    ? [scopedWallet]
    : await loadPersonEvmWalletAddresses(args.personId)
  if (wallets.length === 0) {
    return {
      aggregate: null,
      vaultDetails,
      partial: morphoCatalog.length === 0 && ledgityCatalog.length === 0,
    }
  }

  let partial = morphoCatalog.length === 0 && ledgityCatalog.length === 0
  let aggregate: VaultAggregate | null = null

  await Promise.all(
    wallets.map(async (walletAddress) => {
      try {
        const row = await fetchDefiVaultPosition({
          personId: args.personId,
          config,
          vaultAddress: normalizedVault,
          walletAddress,
        })

        if (!row || BigInt(row.assets || '0') <= BigInt(0)) return

        const chainId = isLedgityConfig(config) ? LEDGITY_CHAIN_ID : (config.chainId ?? MORPHO_CHAIN_ID)
        const principalNetRaw = await loadPrincipalNetRaw({
          personId: args.personId,
          vaultAddress: normalizedVault,
          chainId,
          walletAddress,
        }).catch(() => null)

        const mapped = mapDefiVaultPosition({
          config,
          row,
          vaultAddress: normalizedVault,
          principalNetRaw,
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
          integrationMode: isLedgityConfig(config) ? 'ledgity_vault' : 'direct_morpho',
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
  walletAddress?: string | null
  mapTransactions: (
    rows: LedgerTransactionRow[],
    currentBalanceReference: number,
  ) => {
    transactions: PortalSavingsVaultTransaction[]
    historyPoints: number[]
  }
}): Promise<PortalSavingsVaultDetailPayload | null> {
  const normalizedVault = normalizeVaultAddress(args.vaultAddress)
  const walletAddress = args.walletAddress?.trim().toLowerCase() || undefined
  const { aggregate, vaultDetails, partial: livePartial } = await loadSingleVaultLiveAggregate({
    personId: args.personId,
    vaultAddress: normalizedVault,
    walletAddress,
  })

  if (!vaultDetails) return null

  const integrationMode: PortalDefiIntegrationMode =
    vaultDetails.integrationMode === 'ledgity_vault' ? 'ledgity_vault' : 'direct_morpho'

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
        integrationMode,
      }

  const ledgerRows = await loadVaultLedgerTransactions({
    personId: args.personId,
    vaultAddress: normalizedVault,
    walletAddress,
  })
  const displayCurrency = resolveSavingsDisplayCurrency(position.assetSymbol, args.currency)
  const { transactions, historyPoints } = args.mapTransactions(
    ledgerRows,
    resolveSavingsPositionValue(position, displayCurrency),
  )

  const beta =
    integrationMode === 'ledgity_vault'
      ? await getLedgityBetaPortalFlags(args.personId)
      : await getMorphoBetaPortalFlags(args.personId)
  const averageApyBps = vaultDetails.userApyBps ?? position.userApyBps

  return {
    currency: args.currency,
    vaultAddress: normalizedVault,
    vaultName: vaultDetails.name,
    assetSymbol: vaultDetails.asset.symbol,
    integrationMode,
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
