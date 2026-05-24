import { MORPHO_CHAIN_ID } from '@/lib/portal/morphoConstants'
import { resolvePortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'
import { parseHumanAmountToRaw } from '@/lib/portal/morphoVaultFormat'
import {
  assertNoConcurrentPendingGroup,
  assertWithdrawAmountWithinPosition,
  createMorphoLedgerEntries,
  mapPrivyActionStatusToLedgerStatus,
  MorphoVaultLedgerError,
  updatePrivyEarnLedgerFromAction,
} from '@/lib/portal/morphoVaultLedger'
import { mapPrivyEarnWalletAction } from '@/lib/portal/privyEarnFormat'
import type { PortalEarnWalletAction } from '@/lib/portal/privyEarnTypes'
import {
  fetchPrivyEarnVaultPosition,
  fetchPrivyWalletAction,
  postPrivyEarnDeposit,
  postPrivyEarnWithdraw,
} from '@/lib/portal/privyServerClient'
import { resolvePortalEarnWalletIdentity } from '@/lib/portal/resolvePortalEarnWalletIdentity'
import { verifyMorphoTransactionReceipt } from '@/lib/portal/morphoReceiptVerification'
import {
  assertMorphoUsdcBetaAccess,
  assertMorphoUsdcDepositsEnabled,
  assertMorphoUsdcWithdrawsEnabled,
} from '@/lib/portal/morphoUsdcBetaAccess'
import { assertMorphoBetaDepositLimits } from '@/lib/portal/morphoUsdcBetaLimits'
import { emitMorphoLedgerTerminalSupportLog } from '@/lib/portal/morphoBetaSupportEmit'

const TERMINAL = new Set(['succeeded', 'failed', 'rejected'])

export class PrivyEarnVaultConfigError extends Error {
  readonly httpStatus = 404
  readonly code = 'privy.earn.vault_not_published'

  constructor(message = 'Vault non publié.') {
    super(message)
    this.name = 'PrivyEarnVaultConfigError'
  }
}

export async function resolvePublishedPrivyEarnVault(vaultId: string) {
  const configs = await resolvePortalMorphoVaultConfigs({ publishedOnly: true })
  const config = configs.find(
    (row) => row.integrationMode === 'privy_earn' && row.privyVaultId === vaultId,
  )
  if (!config) {
    throw new PrivyEarnVaultConfigError()
  }
  return config
}

async function pollPrivyActionUntilTerminal(args: {
  walletId: string
  actionId: string
  timeoutMs?: number
  intervalMs?: number
}): Promise<Record<string, unknown>> {
  const timeoutMs = args.timeoutMs ?? 180_000
  const intervalMs = args.intervalMs ?? 3_000
  const started = Date.now()
  let latest = await fetchPrivyWalletAction(args.walletId, args.actionId)
  while (!TERMINAL.has(String(latest.status ?? '').toLowerCase()) && Date.now() - started < timeoutMs) {
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
    latest = await fetchPrivyWalletAction(args.walletId, args.actionId)
  }
  return latest
}

async function finalizePrivyEarnLedger(args: {
  ledgerEntryId: string
  personId: string
  walletId: string
  actionId: string
  vaultAddress: string
  operation: 'deposit' | 'withdraw'
}): Promise<PortalEarnWalletAction> {
  const raw = await pollPrivyActionUntilTerminal({
    walletId: args.walletId,
    actionId: args.actionId,
  })
  const action = mapPrivyEarnWalletAction(raw)
  let ledgerStatus = mapPrivyActionStatusToLedgerStatus(action.status)
  let blockNumber: bigint | null = null
  let errorMessage = action.failureMessage

  if (action.transactionHash && ledgerStatus === 'success') {
    try {
      const receipt = await verifyMorphoTransactionReceipt({
        txHash: action.transactionHash,
        expectedChainId: MORPHO_CHAIN_ID,
      })
      ledgerStatus = receipt.status === 'success' ? 'success' : 'reverted'
      blockNumber = receipt.blockNumber
      if (receipt.status === 'reverted') {
        errorMessage = 'Transaction revert on-chain.'
      }
    } catch (error) {
      ledgerStatus = 'failed'
      errorMessage = error instanceof Error ? error.message : 'Receipt invalide.'
    }
  } else if (ledgerStatus === 'failed') {
    errorMessage = action.failureMessage ?? 'Opération Privy Earn échouée.'
  }

  await updatePrivyEarnLedgerFromAction({
    ledgerEntryId: args.ledgerEntryId,
    personId: args.personId,
    privyActionId: action.id,
    status: ledgerStatus,
    txHash: action.transactionHash ?? null,
    blockNumber,
    errorMessage: errorMessage ?? null,
  })

  if (ledgerStatus !== 'success' && ledgerStatus !== 'pending') {
    emitMorphoLedgerTerminalSupportLog({
      id: args.ledgerEntryId,
      personId: args.personId,
      vaultAddress: args.vaultAddress,
      operation: args.operation,
      status: ledgerStatus,
      txHash: action.transactionHash ?? null,
      errorMessage: errorMessage ?? null,
    })
  }

  return {
    ...action,
    status: ledgerStatus === 'success' ? 'succeeded' : ledgerStatus === 'pending' ? action.status : 'failed',
    failureMessage: errorMessage,
  }
}

export async function executePrivyEarnOperation(args: {
  personId: string
  walletId: string
  vaultId: string
  operation: 'deposit' | 'withdraw'
  amount: string
  idempotencyKey: string
  authorizationSignature?: string
  requestExpiry?: string
}): Promise<PortalEarnWalletAction> {
  await assertMorphoUsdcBetaAccess(args.personId)

  const config = await resolvePublishedPrivyEarnVault(args.vaultId)
  const vaultAddress = config.vaultAddress
  if (!vaultAddress) {
    throw new PrivyEarnVaultConfigError('Adresse vault manquante pour ce vault Privy Earn.')
  }

  if (args.operation === 'deposit') {
    assertMorphoUsdcDepositsEnabled()
  } else {
    assertMorphoUsdcWithdrawsEnabled()
  }

  const walletIdentity = await resolvePortalEarnWalletIdentity({
    personId: args.personId,
    privyWalletId: args.walletId,
  })

  const position = await fetchPrivyEarnVaultPosition(args.walletId, args.vaultId)
  const assetRaw = (position.asset ?? {}) as Record<string, unknown>
  const assetDecimals = Number(assetRaw.decimals ?? 6)
  const assetSymbol = String(assetRaw.symbol ?? 'USDC').toUpperCase()

  if (args.operation === 'deposit') {
    await assertMorphoBetaDepositLimits({
      personId: args.personId,
      amount: args.amount,
      assetDecimals,
    })
  }

  const amountRaw = parseHumanAmountToRaw(args.amount, assetDecimals).toString()

  if (args.operation === 'withdraw') {
    const assetsInVault = String(position.assets_in_vault ?? position.assetsInVault ?? '0')
    await assertWithdrawAmountWithinPosition({
      amountRaw: BigInt(amountRaw),
      assetsInVaultRaw: assetsInVault,
    })
  }

  const existing = await assertNoConcurrentPendingGroup({
    personId: args.personId,
    vaultAddress,
    idempotencyKey: args.idempotencyKey,
  })

  const succeeded = existing.find((row) => row.operation === args.operation && row.status === 'success')
  if (succeeded?.privyActionId) {
    const raw = await fetchPrivyWalletAction(args.walletId, succeeded.privyActionId)
    return mapPrivyEarnWalletAction(raw)
  }

  let ledgerEntry = existing.find((row) => row.operation === args.operation)
  if (!ledgerEntry) {
    const created = await createMorphoLedgerEntries([
      {
        personId: args.personId,
        vaultAddress,
        chainId: config.chainId,
        chainType: 'evm',
        walletAddress: walletIdentity.walletAddress,
        privyWalletId: walletIdentity.privyWalletId,
        operation: args.operation,
        amountRaw,
        assetSymbol,
        assetDecimals,
        idempotencyKey: args.idempotencyKey,
        integrationMode: 'privy_earn',
        txIndex: 0,
        groupKey: args.idempotencyKey,
      },
    ])
    ledgerEntry = created[0]
  }

  if (ledgerEntry.privyActionId) {
    return finalizePrivyEarnLedger({
      ledgerEntryId: ledgerEntry.id,
      personId: args.personId,
      walletId: args.walletId,
      actionId: ledgerEntry.privyActionId,
      vaultAddress,
      operation: args.operation,
    })
  }

  const post =
    args.operation === 'deposit'
      ? postPrivyEarnDeposit
      : postPrivyEarnWithdraw

  const raw = await post({
    walletId: args.walletId,
    vaultId: args.vaultId,
    amount: args.amount,
    authorizationSignature: args.authorizationSignature,
    idempotencyKey: args.idempotencyKey,
    requestExpiry: args.requestExpiry,
  })

  const action = mapPrivyEarnWalletAction(raw)
  if (!action.id) {
    throw new MorphoVaultLedgerError('privy.earn.action_missing', 'Action Privy Earn introuvable.', 502)
  }

  await updatePrivyEarnLedgerFromAction({
    ledgerEntryId: ledgerEntry.id,
    personId: args.personId,
    privyActionId: action.id,
    status: 'pending',
  })

  return finalizePrivyEarnLedger({
    ledgerEntryId: ledgerEntry.id,
    personId: args.personId,
    walletId: args.walletId,
    actionId: action.id,
    vaultAddress,
    operation: args.operation,
  })
}
