import { randomBytes } from 'node:crypto'

import type { OnchainVaultTransaction } from '@prisma/client'
import type { Prisma } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import {
  LEDGITY_CHAIN_ID,
  LEDGITY_EURC_ADDRESS,
  LEDGITY_LYEURC_VAULT,
  LEDGITY_LYUSDC_VAULT,
  LEDGITY_USDC_ADDRESS,
  normalizeVaultAddress,
} from '@/lib/portal/ledgity/ledgityConstants'
import {
  assertNoConcurrentPendingGroup,
  assertWithdrawAmountWithinPosition,
  createMorphoLedgerEntries,
  loadPrincipalNetRaw,
  MorphoVaultLedgerError,
  syncUserVaultPositionFromLedger,
} from '@/lib/portal/morphoVaultLedger'
import {
  getLedgityLocalSandboxPricePerShare,
  getLedgityLocalSandboxYieldBps,
  LEDGITY_LOCAL_SANDBOX_PRIVY_WALLET_ID,
  LEDGITY_LOCAL_SANDBOX_WALLET_ADDRESS,
} from '@/lib/portal/ledgity/ledgityLocalSandboxConfig'
import { buildLedgityLedgerMetadata } from '@/lib/portal/ledgity/ledgityLedgerMetadata'
import type { LedgityDependencyHealth } from '@/lib/portal/ledgity/ledgityVaultMonitoring'
import type {
  LedgityVaultPositionRow,
  PortalLedgityCatalogVault,
  PortalLedgityPreparePayload,
} from '@/lib/portal/ledgity/ledgityVaultTypes'
import type { WalletSourceMetadata } from '@/lib/wallet/executionWalletTypes'

export const SANDBOX_TX_METADATA: Prisma.InputJsonValue = {
  ledgity_sandbox: true,
  source: 'ledgity_local_sandbox',
}

export function isSandboxLedgityIdempotencyKey(idempotencyKey: string): boolean {
  return idempotencyKey.startsWith('ledgity-sandbox-')
}

const USDC_ASSET = {
  address: LEDGITY_USDC_ADDRESS,
  symbol: 'USDC',
  decimals: 6,
}

const EURC_ASSET = {
  address: LEDGITY_EURC_ADDRESS,
  symbol: 'EURC',
  decimals: 6,
}

type SandboxVaultMeta = {
  address: string
  name: string
  symbol: string
  asset: typeof USDC_ASSET | typeof EURC_ASSET
  curator: string
  description: string
  netApy: number
  pricePerShare: number
  tvlUsd: number
  liquidityUsd: number
}

const SANDBOX_VAULTS: SandboxVaultMeta[] = [
  {
    address: LEDGITY_LYUSDC_VAULT,
    name: 'Ledgity lyUSDC',
    symbol: 'lyUSDC',
    asset: USDC_ASSET,
    curator: 'Ledgity',
    description: 'Vault Ledgity lyUSDC sur Base (sandbox local).',
    netApy: 0.09,
    pricePerShare: 1.0578,
    tvlUsd: 12_400_000,
    liquidityUsd: 3_100_000,
  },
  {
    address: LEDGITY_LYEURC_VAULT,
    name: 'Ledgity lyEURC',
    symbol: 'lyEURC',
    asset: EURC_ASSET,
    curator: 'Ledgity',
    description: 'Vault Ledgity lyEURC sur Base (sandbox local).',
    netApy: 0.09,
    pricePerShare: 1.0578,
    tvlUsd: 4_800_000,
    liquidityUsd: 1_200_000,
  },
]

export function generateSandboxTxHash(): string {
  return `0x${randomBytes(32).toString('hex')}`
}

export function applyLedgitySandboxPps(
  principalRaw: bigint,
  pricePerShare?: number,
): bigint {
  const pps = pricePerShare ?? getLedgityLocalSandboxPricePerShare()
  const scaled = BigInt(Math.round(pps * 10_000))
  if (principalRaw <= BigInt(0) || scaled <= BigInt(0)) return principalRaw
  return (principalRaw * scaled) / BigInt(10_000)
}

export function applyLedgitySandboxYield(principalRaw: bigint, yieldBps?: number): bigint {
  const bps = yieldBps ?? getLedgityLocalSandboxYieldBps()
  const withPps = applyLedgitySandboxPps(principalRaw)
  if (withPps <= BigInt(0) || bps <= 0) return withPps
  const bonus = (withPps * BigInt(bps)) / BigInt(10000)
  return withPps + bonus
}

export function getSandboxMockVaultCatalog(vaultAddress: string): PortalLedgityCatalogVault | null {
  const normalized = normalizeVaultAddress(vaultAddress)
  const meta = SANDBOX_VAULTS.find((row) => normalizeVaultAddress(row.address) === normalized)
  if (!meta) return null
  return {
    address: meta.address,
    name: meta.name,
    symbol: meta.symbol,
    listed: true,
    asset: meta.asset,
    netApy: meta.netApy,
    pricePerShare: meta.pricePerShare,
    tvlUsd: meta.tvlUsd,
    liquidityUsd: meta.liquidityUsd,
    curator: meta.curator,
    description: meta.description,
  }
}

export function listSandboxMockVaultCatalogs(addresses?: string[]): PortalLedgityCatalogVault[] {
  const normalized = addresses?.map((row) => normalizeVaultAddress(row))
  return SANDBOX_VAULTS.filter((row) => {
    if (!normalized?.length) return true
    return normalized.includes(normalizeVaultAddress(row.address))
  }).map((meta) => getSandboxMockVaultCatalog(meta.address)!)
}

async function markSandboxLedgerMetadata(
  entryIds: string[],
  args: {
    walletSource?: WalletSourceMetadata
    vaultAddress: string
    assetSymbol: string
  },
): Promise<void> {
  if (entryIds.length === 0) return
  const metadata = buildLedgityLedgerMetadata({
    vaultAddress: args.vaultAddress,
    assetSymbol: args.assetSymbol,
    walletSource: args.walletSource,
    ppsAtTx: getLedgityLocalSandboxPricePerShare(),
    extra: SANDBOX_TX_METADATA as Record<string, unknown>,
  })
  await prisma.onchainVaultTransaction.updateMany({
    where: { id: { in: entryIds } },
    data: { metadataJson: metadata },
  })
}

async function resolveSandboxPositionAssetsRaw(args: {
  personId: string
  vaultAddress: string
  walletAddress: string
  chainId?: number
}): Promise<{ assetsRaw: string; sharesRaw: string; principalNetRaw: string | null; asset: typeof USDC_ASSET | typeof EURC_ASSET }> {
  const normalizedVault = normalizeVaultAddress(args.vaultAddress)
  const normalizedWallet = args.walletAddress.trim().toLowerCase()
  const chainId = args.chainId ?? LEDGITY_CHAIN_ID
  const catalog = getSandboxMockVaultCatalog(args.vaultAddress)
  const asset = catalog?.asset ?? USDC_ASSET

  const principalNetRaw = await loadPrincipalNetRaw({
    personId: args.personId,
    vaultAddress: args.vaultAddress,
    chainId,
    walletAddress: args.walletAddress,
  })

  if (!principalNetRaw || principalNetRaw === '0') {
    return { assetsRaw: '0', sharesRaw: '0', principalNetRaw: null, asset }
  }

  const withYield = applyLedgitySandboxYield(
    BigInt(principalNetRaw),
    getLedgityLocalSandboxYieldBps(),
  ).toString()

  const stored = await prisma.userVaultPosition.findFirst({
    where: {
      personId: args.personId,
      vaultAddress: normalizedVault,
      walletAddress: normalizedWallet,
      chainId,
    },
    select: { lastAssetsRaw: true, lastSharesRaw: true },
  })

  const assetsRaw =
    stored?.lastAssetsRaw && BigInt(stored.lastAssetsRaw) > BigInt(withYield)
      ? stored.lastAssetsRaw
      : withYield
  const sharesRaw =
    stored?.lastSharesRaw && BigInt(stored.lastSharesRaw) > BigInt(principalNetRaw)
      ? stored.lastSharesRaw
      : principalNetRaw

  return {
    assetsRaw,
    sharesRaw,
    principalNetRaw,
    asset,
  }
}

export async function fetchSandboxLedgityVaultPosition(args: {
  personId: string
  vaultAddress: string
  walletAddress: string
  chainId?: number
}): Promise<LedgityVaultPositionRow | null> {
  const position = await resolveSandboxPositionAssetsRaw(args)
  if (position.assetsRaw === '0') return null

  const assetsUsd = Number(position.assetsRaw) / 10 ** position.asset.decimals

  return {
    assets: position.assetsRaw,
    shares: position.sharesRaw,
    assetsUsd: Number.isFinite(assetsUsd) ? assetsUsd : null,
    asset: position.asset,
  }
}

async function sandboxUpdateLedgerSuccess(args: {
  ledgerEntryId: string
  personId: string
  txHash?: string
}): Promise<OnchainVaultTransaction> {
  const entry = await prisma.onchainVaultTransaction.findFirst({
    where: { id: args.ledgerEntryId, personId: args.personId },
  })
  if (!entry) {
    throw new MorphoVaultLedgerError('ledgity.ledger_not_found', 'Entrée ledger introuvable.', 404)
  }
  if (entry.status === 'success') return entry

  const txHash = args.txHash ?? generateSandboxTxHash()
  const position = await resolveSandboxPositionAssetsRaw({
    personId: entry.personId,
    vaultAddress: entry.vaultAddress,
    walletAddress: entry.walletAddress,
    chainId: entry.chainId,
  })

  const updated = await prisma.onchainVaultTransaction.update({
    where: { id: entry.id },
    data: {
      txHash,
      blockNumber: BigInt(1),
      status: 'success',
      errorMessage: null,
    },
  })

  if (updated.operation === 'deposit' || updated.operation === 'withdraw') {
    await syncUserVaultPositionFromLedger({
      personId: updated.personId,
      vaultAddress: updated.vaultAddress,
      chainId: updated.chainId,
      walletAddress: updated.walletAddress,
      privyWalletId: updated.privyWalletId,
      assetSymbol: updated.assetSymbol,
      assetDecimals: updated.assetDecimals,
      lastAssetsRaw: position.assetsRaw,
      lastSharesRaw: position.sharesRaw,
      costBasisUnknown: position.principalNetRaw == null,
    })
  }

  return updated
}

async function completeSandboxLedgerGroup(args: {
  personId: string
  vaultAddress: string
  walletAddress: string
  idempotencyKey: string
  operation: 'deposit' | 'withdraw'
  amountRaw: string
  assetSymbol: string
  assetDecimals: number
  privyWalletId?: string | null
  integrationMode: 'ledgity_vault'
  walletSource?: WalletSourceMetadata
}): Promise<OnchainVaultTransaction[]> {
  const existing = await assertNoConcurrentPendingGroup({
    personId: args.personId,
    vaultAddress: args.vaultAddress,
    idempotencyKey: args.idempotencyKey,
  })

  const primarySucceeded = existing.filter((row) => row.status === 'success' && row.operation === args.operation)
  if (primarySucceeded.length > 0) return primarySucceeded

  let entries = existing.filter((row) => row.operation === args.operation)
  if (entries.length === 0) {
    entries = await createMorphoLedgerEntries([
      {
        personId: args.personId,
        vaultAddress: args.vaultAddress,
        chainId: LEDGITY_CHAIN_ID,
        chainType: 'evm',
        walletAddress: args.walletAddress,
        privyWalletId: args.privyWalletId ?? null,
        operation: args.operation,
        amountRaw: args.amountRaw,
        assetSymbol: args.assetSymbol,
        assetDecimals: args.assetDecimals,
        idempotencyKey: args.idempotencyKey,
        integrationMode: args.integrationMode,
        txIndex: 0,
        groupKey: args.idempotencyKey,
      },
    ])
    await markSandboxLedgerMetadata(entries.map((row) => row.id), {
      walletSource: args.walletSource,
      vaultAddress: args.vaultAddress,
      assetSymbol: args.assetSymbol,
    })
  }

  const completed: OnchainVaultTransaction[] = []
  for (const entry of entries) {
    completed.push(
      await sandboxUpdateLedgerSuccess({
        ledgerEntryId: entry.id,
        personId: args.personId,
      }),
    )
  }
  return completed
}

export async function executeSandboxLedgityOperation(args: {
  personId: string
  vaultAddress: string
  walletAddress: string
  operation: 'deposit' | 'withdraw'
  amountRaw: string
  assetSymbol: string
  assetDecimals: number
  idempotencyKey: string
  walletSource?: WalletSourceMetadata
}): Promise<PortalLedgityPreparePayload & { serverCompleted: true }> {
  const position = await resolveSandboxPositionAssetsRaw({
    personId: args.personId,
    vaultAddress: args.vaultAddress,
    walletAddress: args.walletAddress,
  })

  if (args.operation === 'withdraw') {
    await assertWithdrawAmountWithinPosition({
      amountRaw: BigInt(args.amountRaw),
      assetsInVaultRaw: position.assetsRaw,
    })
  }

  const entries = await completeSandboxLedgerGroup({
    personId: args.personId,
    vaultAddress: args.vaultAddress,
    walletAddress: args.walletAddress,
    idempotencyKey: args.idempotencyKey,
    operation: args.operation,
    amountRaw: args.amountRaw,
    assetSymbol: args.assetSymbol,
    assetDecimals: args.assetDecimals,
    integrationMode: 'ledgity_vault',
    walletSource: args.walletSource,
  })

  return {
    transactions: [],
    ledgerEntries: entries.map((row) => ({
      id: row.id,
      operation: row.operation as 'approve' | 'deposit' | 'withdraw',
      txIndex: row.txIndex,
    })),
    groupKey: args.idempotencyKey,
    idempotencyKey: args.idempotencyKey,
    serverCompleted: true,
  }
}

export {
  LEDGITY_LOCAL_SANDBOX_PRIVY_WALLET_ID,
  LEDGITY_LOCAL_SANDBOX_WALLET_ADDRESS,
  USDC_ASSET,
  EURC_ASSET,
}

export function getSandboxLedgityDependencyHealth(): LedgityDependencyHealth {
  return {
    baseRpc: {
      ok: true,
      latencyMs: 1,
      activeProvider: 'local-sandbox',
      usedFallback: false,
      publicRpcAsPrimary: false,
      providers: [{ label: 'local-sandbox', ok: true, latencyMs: 1, isPublic: false }],
    },
  }
}

export async function fetchSandboxLedgityOnchainPositionForReconciliation(args: {
  personId: string
  vaultAddress: string
  walletAddress: string
}): Promise<{ assetsRaw: string; sharesRaw: string; ppsAtReconcile: string | null }> {
  const position = await resolveSandboxPositionAssetsRaw(args)
  return {
    assetsRaw: position.assetsRaw,
    sharesRaw: position.sharesRaw,
    ppsAtReconcile: String(getLedgityLocalSandboxPricePerShare()),
  }
}
