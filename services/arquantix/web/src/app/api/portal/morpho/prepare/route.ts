import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import type { Prisma } from '@prisma/client'

import { isValidEvmAddress, MORPHO_CHAIN_ID } from '@/lib/portal/morphoConstants'
import {
  morphoLedgerErrorResponse,
  morphoRpcErrorResponse,
} from '@/lib/portal/portalVaultRouteHelpers'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
import { fetchMorphoVaultPosition, fetchMorphoVaultsByAddresses } from '@/lib/portal/morphoGraphql'
import { isMorphoLocalSandboxEnabled } from '@/lib/portal/morphoLocalSandboxConfig'
import {
  executeSandboxDirectMorphoOperation,
  getSandboxMockVaultCatalog,
} from '@/lib/portal/mocks/morphoLocalSandbox'
import { parseHumanAmountToRaw } from '@/lib/portal/morphoVaultFormat'
import {
  assertNoConcurrentPendingGroup,
  assertWithdrawAmountWithinPosition,
  createMorphoLedgerEntries,
  MorphoVaultLedgerError,
} from '@/lib/portal/morphoVaultLedger'
import { prepareMorphoTxSchema } from '@/lib/portal/morphoVaultValidation'
import { buildMorphoVaultTransactions } from '@/lib/portal/morphoVaultTx'
import { resolvePortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
import {
  assertMorphoUsdcBetaAccess,
  assertMorphoUsdcDepositsEnabled,
  assertMorphoUsdcWithdrawsEnabled,
} from '@/lib/portal/morphoUsdcBetaAccess'
import { assertMorphoBetaDepositLimits } from '@/lib/portal/morphoUsdcBetaLimits'
import { assertPortalVaultDepositTradingAvailable } from '@/lib/portal/vaultDepositValidation'
import type { ExecutionWalletSource, WalletSourceMetadata } from '@/lib/wallet/executionWalletTypes'

function parseWalletSourceMetadata(body: unknown): WalletSourceMetadata {
  if (!body || typeof body !== 'object') {
    return { wallet_source: 'privy_embedded' }
  }
  const row = body as Record<string, unknown>
  const source = row.wallet_source ?? row.walletSource
  const walletSource: ExecutionWalletSource =
    source === 'external_evm' ? 'external_evm' : 'privy_embedded'
  const externalWalletId =
    typeof row.external_wallet_id === 'string'
      ? row.external_wallet_id
      : typeof row.externalWalletId === 'string'
        ? row.externalWalletId
        : null
  const walletProvider =
    row.wallet_provider === 'metamask' ||
    row.wallet_provider === 'walletconnect' ||
    row.wallet_provider === 'injected' ||
    row.wallet_provider === 'local_mock'
      ? row.wallet_provider
      : row.walletProvider === 'metamask' ||
          row.walletProvider === 'walletconnect' ||
          row.walletProvider === 'injected' ||
          row.walletProvider === 'local_mock'
        ? row.walletProvider
        : null

  return {
    wallet_source: walletSource,
    external_wallet_id: externalWalletId,
    wallet_provider: walletProvider,
  }
}

function parsePrivyWalletIdFromBody(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  const row = body as Record<string, unknown>
  const value = row.privy_wallet_id ?? row.privyWalletId
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

function parsePrepareBody(body: unknown) {
  if (!body || typeof body !== 'object') {
    throw new z.ZodError([])
  }
  const row = body as Record<string, unknown>
  return prepareMorphoTxSchema.parse({
    vaultAddress: row.vault_address ?? row.vaultAddress,
    walletAddress: row.wallet_address ?? row.walletAddress,
    operation: row.operation,
    amount: row.amount,
    idempotencyKey: row.idempotency_key ?? row.idempotencyKey,
  })
}

function classifyLedgerOperation(
  txOperation: 'approve' | 'deposit' | 'withdraw' | undefined,
  fallback: 'deposit' | 'withdraw',
): 'approve' | 'deposit' | 'withdraw' {
  if (txOperation === 'approve' || txOperation === 'deposit' || txOperation === 'withdraw') {
    return txOperation
  }
  return fallback
}

/** Prépare la séquence de txs on-chain (approve + deposit bundler, ou withdraw direct). */
export async function POST(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    await assertMorphoUsdcBetaAccess(personId)

    const body = await request.json()
    const parsed = parsePrepareBody(body)
    const walletSource = parseWalletSourceMetadata(body)
    const privyWalletIdFromBody = parsePrivyWalletIdFromBody(body)
    const vaultAddress = parsed.vaultAddress.trim()
    const walletAddress = parsed.walletAddress.trim()
    const idempotencyKey = parsed.idempotencyKey

    if (!isValidEvmAddress(vaultAddress) || !isValidEvmAddress(walletAddress)) {
      return NextResponse.json({ error: 'Adresses invalides.' }, { status: 400 })
    }

    await assertPortalWalletAddressOwnership({ personId, walletAddress })

    const configs = await resolvePortalMorphoVaultConfigs({ publishedOnly: true })
    const config = configs.find((row) => row.vaultAddress.toLowerCase() === vaultAddress.toLowerCase())
    if (!config) {
      return NextResponse.json({ error: 'Vault non publié.' }, { status: 404 })
    }
    if (config.integrationMode !== 'direct_morpho') {
      return NextResponse.json({ error: 'Ce vault n’est pas en mode direct_morpho.' }, { status: 400 })
    }

    const gqlRows = isMorphoLocalSandboxEnabled()
      ? (() => {
          const catalog = getSandboxMockVaultCatalog(vaultAddress)
          return catalog ? [catalog] : []
        })()
      : await fetchMorphoVaultsByAddresses({ addresses: [vaultAddress] })
    const gqlVault = gqlRows[0]
    const assetDecimals = gqlVault?.asset.decimals ?? 6
    const assetSymbol = gqlVault?.asset.symbol ?? 'USDC'

    if (parsed.operation === 'deposit') {
      assertMorphoUsdcDepositsEnabled()
      await assertMorphoBetaDepositLimits({
        personId,
        amount: parsed.amount,
        assetDecimals,
      })
      await assertPortalVaultDepositTradingAvailable(parsed.amount)
    } else {
      assertMorphoUsdcWithdrawsEnabled()
    }

    const amountRaw = parseHumanAmountToRaw(parsed.amount, assetDecimals).toString()

    if (isMorphoLocalSandboxEnabled()) {
      return NextResponse.json(
        await executeSandboxDirectMorphoOperation({
          personId,
          vaultAddress,
          walletAddress,
          operation: parsed.operation,
          amountRaw,
          assetSymbol,
          assetDecimals,
          idempotencyKey,
          walletSource,
        }),
      )
    }

    if (parsed.operation === 'withdraw') {
      const position = await fetchMorphoVaultPosition({ vaultAddress, walletAddress })
      const assetsInVault = position?.assets ?? '0'
      await assertWithdrawAmountWithinPosition({
        amountRaw: BigInt(amountRaw),
        assetsInVaultRaw: assetsInVault,
      })
    }

    const existing = await assertNoConcurrentPendingGroup({
      personId,
      vaultAddress,
      idempotencyKey,
    })

    const primarySucceeded = existing.some(
      (row) =>
        row.status === 'success' &&
        (row.operation === parsed.operation || (parsed.operation === 'deposit' && row.operation === 'deposit')),
    )
    if (primarySucceeded) {
      throw new MorphoVaultLedgerError(
        'morpho.already_completed',
        'Cette opération a déjà été confirmée.',
        409,
      )
    }

    const transactions = await buildMorphoVaultTransactions({
      vaultAddress,
      walletAddress,
      operation: parsed.operation,
      amount: parsed.amount,
      assetDecimals,
      morphoVaultVersion: gqlVault?.version ?? null,
    })

    const groupKey = idempotencyKey
    let ledgerEntries = existing

    if (ledgerEntries.length === 0) {
      const approveCount = transactions.filter((tx) => tx.operation === 'approve').length
      ledgerEntries = await createMorphoLedgerEntries(
        transactions.map((tx, index) => {
          const operation = classifyLedgerOperation(tx.operation, parsed.operation)
          const txIndex = operation === 'approve' ? index : index - approveCount
          return {
            personId,
            vaultAddress,
            chainId: MORPHO_CHAIN_ID,
            chainType: 'evm',
            walletAddress,
            privyWalletId: privyWalletIdFromBody,
            operation,
            amountRaw: operation === 'approve' ? '0' : amountRaw,
            assetSymbol,
            assetDecimals,
            idempotencyKey,
            integrationMode: 'direct_morpho',
            txIndex: Math.max(0, txIndex),
            groupKey,
            metadataJson: walletSource as Prisma.InputJsonValue,
          }
        }),
      )
    }

    return NextResponse.json({
      transactions,
      ledgerEntries: ledgerEntries.map((row) => ({
        id: row.id,
        operation: row.operation,
        txIndex: row.txIndex,
      })),
      groupKey,
      idempotencyKey,
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request data', issues: error.issues }, { status: 400 })
    }
    const rpcResponse = morphoRpcErrorResponse(error, 'morpho.prepare')
    if (rpcResponse) return rpcResponse
    const ledgerResponse = morphoLedgerErrorResponse(error)
    if (ledgerResponse.status !== 500) return ledgerResponse
    console.error('[api/portal/morpho/prepare POST]', error)
    const message = error instanceof Error ? error.message : 'Erreur interne.'
    return NextResponse.json({ code: 'morpho.prepare_failed', message }, { status: 500 })
  }
}
