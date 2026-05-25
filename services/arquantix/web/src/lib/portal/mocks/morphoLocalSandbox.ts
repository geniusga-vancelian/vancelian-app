import { randomBytes } from 'node:crypto'

import type { OnchainVaultTransaction, PortalMorphoVaultConfig } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import {
  MORPHO_CHAIN_ID,
  normalizeVaultAddress,
} from '@/lib/portal/morphoConstants'
import type { MorphoVaultPositionRow } from '@/lib/portal/morphoGraphql'
import {
  assertNoConcurrentPendingGroup,
  assertWithdrawAmountWithinPosition,
  createMorphoLedgerEntries,
  loadPrincipalNetRaw,
  MorphoVaultLedgerError,
  syncUserVaultPositionFromLedger,
} from '@/lib/portal/morphoVaultLedger'
import {
  getMorphoLocalSandboxYieldBps,
  MORPHO_LOCAL_SANDBOX_PRIVY_WALLET_ID,
  MORPHO_LOCAL_SANDBOX_WALLET_ADDRESS,
} from '@/lib/portal/morphoLocalSandboxConfig'
import { compareMorphoReconciliationAssets } from '@/lib/portal/morphoVaultMonitoring'
import type { MorphoDependencyHealth } from '@/lib/portal/morphoVaultMonitoring'
import type { PortalMorphoCatalogVault } from '@/lib/portal/morphoVaultTypes'
import type { PortalMorphoPreparePayload } from '@/lib/portal/morphoVaultTypes'
import type { Prisma } from '@prisma/client'
import type { WalletSourceMetadata } from '@/lib/wallet/executionWalletTypes'

export const SANDBOX_TX_METADATA: Prisma.InputJsonValue = {
  morpho_sandbox: true,
  source: 'morpho_local_sandbox',
}

export function isSandboxMorphoIdempotencyKey(idempotencyKey: string): boolean {
  return idempotencyKey.startsWith('sandbox-')
}

async function markSandboxLedgerMetadata(
  entryIds: string[],
  walletSource?: WalletSourceMetadata,
): Promise<void> {
  if (entryIds.length === 0) return
  const metadata: Prisma.InputJsonValue = {
    ...(SANDBOX_TX_METADATA as Record<string, unknown>),
    ...(walletSource?.wallet_source ? { wallet_source: walletSource.wallet_source } : {}),
    ...(walletSource?.external_wallet_id ? { external_wallet_id: walletSource.external_wallet_id } : {}),
    ...(walletSource?.wallet_provider ? { wallet_provider: walletSource.wallet_provider } : {}),
  }
  await prisma.onchainVaultTransaction.updateMany({
    where: { id: { in: entryIds } },
    data: { metadataJson: metadata },
  })
}

const USDC_ASSET = {
  address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
  symbol: 'USDC',
  decimals: 6,
}

type SandboxVaultMeta = {
  address: string
  name: string
  curator: string
  description: string
  netApy: number
  tvlUsd: number
  liquidityUsd: number
  version: 'v1' | 'v2'
}

const SANDBOX_VAULTS: SandboxVaultMeta[] = [
  {
    address: '0xbeef0e0834849acc03f0089f01f4f1eeb06873c9',
    name: 'Steakhouse Prime USDC',
    curator: 'Steakhouse Financial',
    description: 'Steakhouse Prime Instant — vault Morpho V2 USDC sur Base (sandbox local).',
    netApy: 0.052,
    tvlUsd: 42_500_000,
    liquidityUsd: 8_200_000,
    version: 'v2',
  },
  {
    address: '0x050ce30b927da55177a4914ec73480238bad56f0',
    name: 'Gauntlet USDC Prime',
    curator: 'Gauntlet',
    description: 'Vault Morpho V2 USDC Gauntlet Prime sur Base (sandbox local).',
    netApy: 0.048,
    tvlUsd: 28_300_000,
    liquidityUsd: 5_600_000,
    version: 'v2',
  },
]

export function generateSandboxTxHash(): string {
  return `0x${randomBytes(32).toString('hex')}`
}

export function applySandboxYield(principalRaw: bigint, yieldBps?: number): bigint {
  const bps = yieldBps ?? getMorphoLocalSandboxYieldBps()
  if (principalRaw <= BigInt(0) || bps <= 0) return principalRaw
  const bonus = (principalRaw * BigInt(bps)) / BigInt(10000)
  return principalRaw + bonus
}

export function getSandboxMockVaultCatalog(vaultAddress: string): PortalMorphoCatalogVault | null {
  const normalized = normalizeVaultAddress(vaultAddress)
  const meta = SANDBOX_VAULTS.find((row) => normalizeVaultAddress(row.address) === normalized)
  if (!meta) return null
  return {
    address: meta.address,
    name: meta.name,
    symbol: 'USDC',
    listed: true,
    version: meta.version,
    asset: USDC_ASSET,
    netApy: meta.netApy,
    tvlUsd: meta.tvlUsd,
    liquidityUsd: meta.liquidityUsd,
    curator: meta.curator,
    description: meta.description,
  }
}

export function listSandboxMockVaultCatalogs(addresses?: string[]): PortalMorphoCatalogVault[] {
  const normalized = addresses?.map((row) => normalizeVaultAddress(row))
  return SANDBOX_VAULTS.filter((row) => {
    if (!normalized?.length) return true
    return normalized.includes(normalizeVaultAddress(row.address))
  }).map((meta) => getSandboxMockVaultCatalog(meta.address)!)
}

export function listSandboxVaultAddresses(): string[] {
  return SANDBOX_VAULTS.map((row) => normalizeVaultAddress(row.address))
}

export async function resolveSandboxPositionAssetsRaw(args: {
  personId: string
  vaultAddress: string
  walletAddress: string
  chainId?: number
}): Promise<{ assetsRaw: string; sharesRaw: string; principalNetRaw: string | null }> {
  const normalizedVault = normalizeVaultAddress(args.vaultAddress)
  const normalizedWallet = args.walletAddress.trim().toLowerCase()
  const chainId = args.chainId ?? MORPHO_CHAIN_ID

  const principalNetRaw = await loadPrincipalNetRaw({
    personId: args.personId,
    vaultAddress: args.vaultAddress,
    chainId,
    walletAddress: args.walletAddress,
  })

  if (!principalNetRaw || principalNetRaw === '0') {
    return { assetsRaw: '0', sharesRaw: '0', principalNetRaw: null }
  }

  const withYield = applySandboxYield(BigInt(principalNetRaw)).toString()

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
  const sharesRaw = stored?.lastSharesRaw && BigInt(stored.lastSharesRaw) > BigInt(withYield)
    ? stored.lastSharesRaw
    : assetsRaw

  return {
    assetsRaw,
    sharesRaw,
    principalNetRaw,
  }
}

export async function fetchSandboxMorphoVaultPosition(args: {
  personId: string
  vaultAddress: string
  walletAddress: string
  chainId?: number
}): Promise<MorphoVaultPositionRow | null> {
  const position = await resolveSandboxPositionAssetsRaw(args)
  if (position.assetsRaw === '0') return null

  const principal = BigInt(position.principalNetRaw || '0')
  const assetsUsd = Number(position.assetsRaw) / 1_000_000

  return {
    assets: position.assetsRaw,
    shares: position.sharesRaw,
    assetsUsd: Number.isFinite(assetsUsd) ? assetsUsd : null,
    asset: USDC_ASSET,
  }
}

export async function sandboxUpdateLedgerSuccess(args: {
  ledgerEntryId: string
  personId: string
  txHash?: string
}): Promise<OnchainVaultTransaction> {
  const entry = await prisma.onchainVaultTransaction.findFirst({
    where: { id: args.ledgerEntryId, personId: args.personId },
  })
  if (!entry) {
    throw new MorphoVaultLedgerError('morpho.ledger_not_found', 'Entrée ledger introuvable.', 404)
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
  integrationMode: 'direct_morpho'
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
        chainId: MORPHO_CHAIN_ID,
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
    await markSandboxLedgerMetadata(entries.map((row) => row.id), args.walletSource)
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

export async function executeSandboxDirectMorphoOperation(args: {
  personId: string
  vaultAddress: string
  walletAddress: string
  operation: 'deposit' | 'withdraw'
  amountRaw: string
  assetSymbol: string
  assetDecimals: number
  idempotencyKey: string
  walletSource?: WalletSourceMetadata
}): Promise<PortalMorphoPreparePayload & { serverCompleted: true }> {
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
    integrationMode: 'direct_morpho',
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

export function getSandboxDependencyHealth(): MorphoDependencyHealth {
  return {
    morphoGraphql: { ok: true, latencyMs: 1 },
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

export async function fetchSandboxOnchainPositionForReconciliation(args: {
  personId: string
  config: PortalMorphoVaultConfig
  walletAddress: string
}): Promise<{ assetsRaw: string; sharesRaw: string }> {
  const position = await resolveSandboxPositionAssetsRaw({
    personId: args.personId,
    vaultAddress: args.config.vaultAddress,
    walletAddress: args.walletAddress,
    chainId: args.config.chainId,
  })
  return {
    assetsRaw: position.assetsRaw,
    sharesRaw: position.sharesRaw,
  }
}

export async function runSandboxMorphoReconciliationItem(args: {
  personId: string
  vaultAddress: string
  walletAddress: string
}): Promise<{
  ledgerAssetsRaw: string
  onchainAssetsRaw: string
  status: ReturnType<typeof compareMorphoReconciliationAssets>
}> {
  const position = await resolveSandboxPositionAssetsRaw({
    personId: args.personId,
    vaultAddress: args.vaultAddress,
    walletAddress: args.walletAddress,
  })
  const ledgerAssetsRaw = position.assetsRaw
  const onchainAssetsRaw = position.assetsRaw
  return {
    ledgerAssetsRaw,
    onchainAssetsRaw,
    status: compareMorphoReconciliationAssets({ ledgerAssetsRaw, onchainAssetsRaw }),
  }
}

export {
  MORPHO_LOCAL_SANDBOX_WALLET_ADDRESS,
  MORPHO_LOCAL_SANDBOX_PRIVY_WALLET_ID,
  USDC_ASSET,
}
