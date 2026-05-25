import { readFileSync } from 'node:fs'
import path from 'node:path'
import { randomUUID } from 'node:crypto'

import type { Prisma } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import { MORPHO_CHAIN_ID, normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import {
  getMorphoLocalSandboxYieldBps,
  isMorphoLocalSandboxEnabled,
  MORPHO_LOCAL_SANDBOX_PRIVY_WALLET_ID,
  MORPHO_LOCAL_SANDBOX_WALLET_ADDRESS,
} from '@/lib/portal/morphoLocalSandboxConfig'
import {
  applySandboxYield,
  generateSandboxTxHash,
  isSandboxMorphoIdempotencyKey,
  listSandboxVaultAddresses,
  SANDBOX_TX_METADATA,
} from '@/lib/portal/mocks/morphoLocalSandbox'
import { parseHumanAmountToRaw } from '@/lib/portal/morphoVaultFormat'
import { getMorphoMonitoringSnapshot } from '@/lib/portal/morphoVaultReconciliation'

type VaultSeedRow = {
  vaultAddress: string
  chainId?: number
  integrationMode: 'direct_morpho'
  privyVaultId?: string | null
  label?: string | null
  description?: string | null
  curator?: string | null
  sortOrder?: number
  isPublished?: boolean
}

export class MorphoSandboxDevError extends Error {
  readonly httpStatus: number
  readonly code: string

  constructor(code: string, message: string, httpStatus = 400) {
    super(message)
    this.name = 'MorphoSandboxDevError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

export function isMorphoSandboxDevRouteAvailable(): boolean {
  return process.env.NODE_ENV !== 'production' && isMorphoLocalSandboxEnabled()
}

export function assertMorphoSandboxDevRouteAvailable(): void {
  if (process.env.NODE_ENV === 'production') {
    throw new MorphoSandboxDevError('morpho.sandbox.dev_forbidden', 'Route dev indisponible en production.', 403)
  }
  if (!isMorphoLocalSandboxEnabled()) {
    throw new MorphoSandboxDevError(
      'morpho.sandbox.disabled',
      'MORPHO_LOCAL_SANDBOX_ENABLED=true requis.',
      403,
    )
  }
}

function sandboxVaultAddresses(): string[] {
  return listSandboxVaultAddresses()
}

function loadSandboxVaultSeedRows(): VaultSeedRow[] {
  const seedPath = path.join(process.cwd(), 'scripts/data/morpho-vault-configs.seed.json')
  const all = JSON.parse(readFileSync(seedPath, 'utf8')) as VaultSeedRow[]
  const allowed = new Set(sandboxVaultAddresses())
  return all.filter((row) => allowed.has(normalizeVaultAddress(row.vaultAddress)))
}

export async function upsertMorphoSandboxVaultConfigs(): Promise<Map<string, string>> {
  const items = loadSandboxVaultSeedRows()
  const configIds = new Map<string, string>()

  for (const item of items) {
    const vaultAddress = normalizeVaultAddress(item.vaultAddress)
    const row = await prisma.portalMorphoVaultConfig.upsert({
      where: { vaultAddress },
      create: {
        id: randomUUID(),
        vaultAddress,
        chainId: item.chainId ?? MORPHO_CHAIN_ID,
        integrationMode: item.integrationMode,
        privyVaultId: item.privyVaultId ?? null,
        label: item.label ?? null,
        description: item.description ?? null,
        curator: item.curator ?? null,
        sortOrder: item.sortOrder ?? 999,
        isPublished: true,
      },
      update: {
        chainId: item.chainId ?? MORPHO_CHAIN_ID,
        integrationMode: item.integrationMode,
        privyVaultId: item.privyVaultId ?? null,
        label: item.label ?? null,
        description: item.description ?? null,
        curator: item.curator ?? null,
        sortOrder: item.sortOrder ?? 999,
        isPublished: true,
      },
    })
    configIds.set(vaultAddress, row.id)
  }

  return configIds
}

export async function upsertMorphoSandboxRegistry(configIds: Map<string, string>): Promise<number> {
  let count = 0
  for (const vaultAddress of sandboxVaultAddresses()) {
    const normalized = normalizeVaultAddress(vaultAddress)
    const configId = configIds.get(normalized)
    const isSteakhouse = normalized === sandboxVaultAddresses()[0]
    await prisma.defiVaultRegistry.upsert({
      where: {
        chainId_vaultAddress: {
          chainId: MORPHO_CHAIN_ID,
          vaultAddress: normalized,
        },
      },
      create: {
        id: randomUUID(),
        chainId: MORPHO_CHAIN_ID,
        vaultAddress: normalized,
        morphoVersion: 'v2',
        assetAddress: '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913',
        assetSymbol: 'USDC',
        assetDecimals: 6,
        name: isSteakhouse ? 'Steakhouse Prime USDC' : 'Gauntlet USDC Prime',
        curator: isSteakhouse ? 'Steakhouse Financial' : 'Gauntlet',
        integrationMode: 'direct_morpho',
        portalConfigId: configId ?? null,
        isActive: true,
        lastSyncedAt: new Date(),
      },
      update: {
        isActive: true,
        portalConfigId: configId ?? null,
        lastSyncedAt: new Date(),
      },
    })
    count += 1
  }
  return count
}

export async function resolveSandboxWalletForPerson(args: {
  personId: string
  walletAddress?: string | null
}): Promise<{ walletAddress: string; privyWalletId: string | null }> {
  if (args.walletAddress?.trim()) {
    return {
      walletAddress: args.walletAddress.trim().toLowerCase(),
      privyWalletId: MORPHO_LOCAL_SANDBOX_PRIVY_WALLET_ID,
    }
  }

  const wallets = await prisma.personCryptoWallet.findMany({
    where: { personId: args.personId, revokedAt: null },
    orderBy: [{ isPrimary: 'desc' }, { createdAt: 'asc' }],
    select: { address: true, metadataJson: true },
  })

  if (wallets.length > 0) {
    const primary = wallets[0]
    const metadata = primary.metadataJson as Record<string, unknown> | null
    const privyWalletId =
      typeof metadata?.privy_wallet_id === 'string'
        ? metadata.privy_wallet_id
        : typeof metadata?.privyWalletId === 'string'
          ? metadata.privyWalletId
          : MORPHO_LOCAL_SANDBOX_PRIVY_WALLET_ID
    return { walletAddress: primary.address.toLowerCase(), privyWalletId }
  }

  return {
    walletAddress: MORPHO_LOCAL_SANDBOX_WALLET_ADDRESS,
    privyWalletId: MORPHO_LOCAL_SANDBOX_PRIVY_WALLET_ID,
  }
}

async function ensureSandboxWalletLinked(args: {
  personId: string
  walletAddress: string
  privyWalletId: string
}): Promise<void> {
  const existing = await prisma.personCryptoWallet.findFirst({
    where: {
      personId: args.personId,
      address: args.walletAddress,
      revokedAt: null,
    },
  })

  if (existing) return

  await prisma.personCryptoWallet.create({
    data: {
      id: randomUUID(),
      personId: args.personId,
      provider: 'privy',
      walletType: 'embedded',
      chainType: 'evm',
      chainId: MORPHO_CHAIN_ID,
      address: args.walletAddress,
      isPrimary: true,
      metadataJson: {
        privy_wallet_id: args.privyWalletId,
        sync_source: 'morpho_local_sandbox_dev',
      },
    },
  })
}

function isSandboxMorphoTransaction(row: {
  idempotencyKey: string
  metadataJson: unknown
}): boolean {
  if (isSandboxMorphoIdempotencyKey(row.idempotencyKey)) return true
  if (!row.metadataJson || typeof row.metadataJson !== 'object') return false
  return (row.metadataJson as Record<string, unknown>).morpho_sandbox === true
}

export async function seedMorphoSandboxForPerson(args: {
  personId: string
  walletAddress?: string | null
  withInitialPosition?: boolean
}): Promise<{
  personId: string
  walletAddress: string
  vaultConfigs: number
  registryEntries: number
  historicalTransactions: number
  positionCreated: boolean
}> {
  const configIds = await upsertMorphoSandboxVaultConfigs()
  const registryEntries = await upsertMorphoSandboxRegistry(configIds)

  const wallet = await resolveSandboxWalletForPerson({
    personId: args.personId,
    walletAddress: args.walletAddress,
  })
  await ensureSandboxWalletLinked({
    personId: args.personId,
    walletAddress: wallet.walletAddress,
    privyWalletId: wallet.privyWalletId ?? MORPHO_LOCAL_SANDBOX_PRIVY_WALLET_ID,
  })

  let historicalTransactions = 0
  let positionCreated = false

  if (args.withInitialPosition !== false) {
    const primaryVault = sandboxVaultAddresses()[0]
    const yieldBps = getMorphoLocalSandboxYieldBps()
    const initialPrincipalRaw = '100000000'
    const depositKey = 'sandbox-seed-deposit-initial'

    const existingDeposit = await prisma.onchainVaultTransaction.findFirst({
      where: { personId: args.personId, idempotencyKey: depositKey },
    })

    if (!existingDeposit) {
      const depositAt = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
      await prisma.onchainVaultTransaction.create({
        data: {
          personId: args.personId,
          vaultAddress: primaryVault,
          chainId: MORPHO_CHAIN_ID,
          chainType: 'evm',
          walletAddress: wallet.walletAddress,
          privyWalletId: wallet.privyWalletId,
          operation: 'deposit',
          amountRaw: initialPrincipalRaw,
          assetSymbol: 'USDC',
          assetDecimals: 6,
          txHash: generateSandboxTxHash(),
          status: 'success',
          idempotencyKey: depositKey,
          integrationMode: 'direct_morpho',
          txIndex: 0,
          groupKey: depositKey,
          blockNumber: BigInt(1),
          metadataJson: SANDBOX_TX_METADATA,
          createdAt: depositAt,
          updatedAt: depositAt,
        },
      })
      historicalTransactions += 1

      await prisma.onchainVaultTransaction.create({
        data: {
          personId: args.personId,
          vaultAddress: primaryVault,
          chainId: MORPHO_CHAIN_ID,
          chainType: 'evm',
          walletAddress: wallet.walletAddress,
          privyWalletId: wallet.privyWalletId,
          operation: 'withdraw',
          amountRaw: '10000000',
          assetSymbol: 'USDC',
          assetDecimals: 6,
          txHash: generateSandboxTxHash(),
          status: 'success',
          idempotencyKey: 'sandbox-seed-withdraw-sample',
          integrationMode: 'direct_morpho',
          txIndex: 0,
          groupKey: 'sandbox-seed-withdraw-sample',
          blockNumber: BigInt(2),
          metadataJson: SANDBOX_TX_METADATA,
          createdAt: new Date(depositAt.getTime() + 2 * 24 * 60 * 60 * 1000),
        },
      })
      historicalTransactions += 1
    }

    const principalNetRaw = '90000000'
    const assetsWithYield = applySandboxYield(BigInt(principalNetRaw), yieldBps).toString()

    await prisma.userVaultPosition.upsert({
      where: {
        personId_chainId_vaultAddress_walletAddress: {
          personId: args.personId,
          chainId: MORPHO_CHAIN_ID,
          vaultAddress: primaryVault,
          walletAddress: wallet.walletAddress,
        },
      },
      create: {
        personId: args.personId,
        vaultAddress: primaryVault,
        chainId: MORPHO_CHAIN_ID,
        chainType: 'evm',
        walletAddress: wallet.walletAddress,
        privyWalletId: wallet.privyWalletId,
        assetSymbol: 'USDC',
        assetDecimals: 6,
        principalNetRaw,
        costBasisUnknown: false,
        lastAssetsRaw: assetsWithYield,
        lastSharesRaw: assetsWithYield,
        lastSyncedAt: new Date(),
      },
      update: {
        privyWalletId: wallet.privyWalletId,
        principalNetRaw,
        costBasisUnknown: false,
        lastAssetsRaw: assetsWithYield,
        lastSharesRaw: assetsWithYield,
        lastSyncedAt: new Date(),
      },
    })
    positionCreated = true
  }

  await prisma.morphoVaultReconciliationRun.create({
    data: {
      startedAt: new Date(),
      finishedAt: new Date(),
      itemsChecked: 1,
      matchedCount: 1,
      mismatchCount: 0,
      missingOnchainCount: 0,
      missingLedgerCount: 0,
      logJson: [] as Prisma.InputJsonValue,
    },
  })

  return {
    personId: args.personId,
    walletAddress: wallet.walletAddress,
    vaultConfigs: configIds.size,
    registryEntries,
    historicalTransactions,
    positionCreated,
  }
}

export async function resetMorphoSandboxForPerson(personId: string): Promise<{
  deletedTransactions: number
  deletedPositions: number
  deletedReconciliationItems: number
}> {
  const vaults = sandboxVaultAddresses()
  const txs = await prisma.onchainVaultTransaction.findMany({
    where: { personId },
    select: { id: true, idempotencyKey: true, metadataJson: true, vaultAddress: true },
  })

  const sandboxTxIds = txs
    .filter((row) => isSandboxMorphoTransaction(row) && vaults.includes(normalizeVaultAddress(row.vaultAddress)))
    .map((row) => row.id)

  const deletedTransactions = sandboxTxIds.length
  if (deletedTransactions > 0) {
    await prisma.onchainVaultTransaction.deleteMany({ where: { id: { in: sandboxTxIds } } })
  }

  const deletedPositions = await prisma.userVaultPosition.deleteMany({
    where: {
      personId,
      vaultAddress: { in: vaults },
    },
  })

  const deletedReconciliationItems = await prisma.morphoVaultReconciliationItem.deleteMany({
    where: {
      personId,
      vaultAddress: { in: vaults },
    },
  })

  return {
    deletedTransactions,
    deletedPositions: deletedPositions.count,
    deletedReconciliationItems: deletedReconciliationItems.count,
  }
}

export async function addMorphoSandboxYieldForPerson(args: {
  personId: string
  amountUsdc: string
  vaultAddress?: string | null
  walletAddress?: string | null
}): Promise<{
  vaultAddress: string
  walletAddress: string
  previousAssetsRaw: string
  nextAssetsRaw: string
  principalNetRaw: string
}> {
  const vaultAddress = normalizeVaultAddress(args.vaultAddress ?? sandboxVaultAddresses()[0])
  const wallet = await resolveSandboxWalletForPerson({
    personId: args.personId,
    walletAddress: args.walletAddress,
  })
  const bonusRaw = parseHumanAmountToRaw(args.amountUsdc, 6).toString()

  const existing = await prisma.userVaultPosition.findFirst({
    where: {
      personId: args.personId,
      vaultAddress,
      walletAddress: wallet.walletAddress,
      chainId: MORPHO_CHAIN_ID,
    },
  })

  if (!existing) {
    throw new MorphoSandboxDevError(
      'morpho.sandbox.no_position',
      'Aucune position sandbox — seed current user d’abord.',
      404,
    )
  }

  const previousAssetsRaw = existing.lastAssetsRaw ?? existing.principalNetRaw ?? '0'
  const nextAssetsRaw = (BigInt(previousAssetsRaw) + BigInt(bonusRaw)).toString()

  await prisma.userVaultPosition.update({
    where: { id: existing.id },
    data: {
      lastAssetsRaw: nextAssetsRaw,
      lastSharesRaw: nextAssetsRaw,
      lastSyncedAt: new Date(),
    },
  })

  return {
    vaultAddress,
    walletAddress: wallet.walletAddress,
    previousAssetsRaw,
    nextAssetsRaw,
    principalNetRaw: existing.principalNetRaw,
  }
}

export async function getMorphoSandboxDevStatus(args: {
  personId?: string | null
}): Promise<{
  sandboxEnabled: boolean
  devRouteAvailable: boolean
  session: {
    authenticated: boolean
    personId: string | null
  }
  wallet: {
    address: string | null
    privyWalletId: string | null
  }
  seed: {
    vaultConfigsPublished: number
    registryActive: number
    userSeeded: boolean
    userPositionCount: number
    userSandboxTxCount: number
  }
  counts: {
    vaults: number
    positions: number
    latestTransactions: number
  }
  monitoring: {
    globalStatus: string
    provider: string | null
    morphoGraphqlMocked: boolean
    baseRpcMocked: boolean
  }
}> {
  const vaults = sandboxVaultAddresses()
  const [publishedVaults, registryActive] = await Promise.all([
    prisma.portalMorphoVaultConfig.count({ where: { isPublished: true, vaultAddress: { in: vaults } } }),
    prisma.defiVaultRegistry.count({ where: { isActive: true, vaultAddress: { in: vaults } } }),
  ])

  let walletAddress: string | null = null
  let privyWalletId: string | null = null
  let userPositionCount = 0
  let userSandboxTxCount = 0
  let positions = 0
  let latestTransactions = 0

  if (args.personId) {
    const wallet = await resolveSandboxWalletForPerson({ personId: args.personId })
    walletAddress = wallet.walletAddress
    privyWalletId = wallet.privyWalletId

    const [positionsForUser, txsForUser, allPositions, recentTxCount] = await Promise.all([
      prisma.userVaultPosition.count({
        where: { personId: args.personId, vaultAddress: { in: vaults } },
      }),
      prisma.onchainVaultTransaction.findMany({
        where: { personId: args.personId, vaultAddress: { in: vaults } },
        select: { idempotencyKey: true, metadataJson: true },
      }),
      prisma.userVaultPosition.count({ where: { vaultAddress: { in: vaults } } }),
      prisma.onchainVaultTransaction.count({
        where: { personId: args.personId, vaultAddress: { in: vaults } },
      }),
    ])

    userPositionCount = positionsForUser
    userSandboxTxCount = txsForUser.filter(isSandboxMorphoTransaction).length
    positions = allPositions
    latestTransactions = recentTxCount
  } else {
    positions = await prisma.userVaultPosition.count({ where: { vaultAddress: { in: vaults } } })
    latestTransactions = await prisma.onchainVaultTransaction.count({
      where: { vaultAddress: { in: vaults } },
    })
  }

  const snapshot = await getMorphoMonitoringSnapshot()

  return {
    sandboxEnabled: isMorphoLocalSandboxEnabled(),
    devRouteAvailable: isMorphoSandboxDevRouteAvailable(),
    session: {
      authenticated: Boolean(args.personId),
      personId: args.personId ?? null,
    },
    wallet: {
      address: walletAddress,
      privyWalletId,
    },
    seed: {
      vaultConfigsPublished: publishedVaults,
      registryActive,
      userSeeded: userPositionCount > 0 || userSandboxTxCount > 0,
      userPositionCount,
      userSandboxTxCount,
    },
    counts: {
      vaults: publishedVaults,
      positions,
      latestTransactions,
    },
    monitoring: {
      globalStatus: snapshot.globalStatus,
      provider: snapshot.dependencyHealth.baseRpc.activeProvider ?? null,
      morphoGraphqlMocked: snapshot.dependencyHealth.morphoGraphql.ok,
      baseRpcMocked: snapshot.dependencyHealth.baseRpc.ok,
    },
  }
}

export function morphoSandboxDevErrorResponse(error: unknown) {
  if (error instanceof MorphoSandboxDevError) {
    return { status: error.httpStatus, body: { code: error.code, message: error.message } }
  }
  return { status: 500, body: { code: 'morpho.sandbox.internal_error', message: 'Erreur interne.' } }
}
