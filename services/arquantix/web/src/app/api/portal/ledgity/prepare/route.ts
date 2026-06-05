import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import {
  assertLedgityBetaAccess,
  assertLedgityDepositsEnabled,
  assertLedgityWithdrawsEnabled,
} from '@/lib/portal/ledgity/ledgityBetaAccess'
import { assertLedgityBetaDepositLimits } from '@/lib/portal/ledgity/ledgityBetaLimits'
import { isLedgityVaultsEnabled } from '@/lib/portal/ledgity/ledgityConfig'
import { LEDGITY_CHAIN_ID, isValidEvmAddress } from '@/lib/portal/ledgity/ledgityConstants'
import { isLedgityLocalSandboxEnabled } from '@/lib/portal/ledgity/ledgityLocalSandboxConfig'
import { fetchLedgityVaultCatalog, fetchLedgityVaultPosition } from '@/lib/portal/ledgity/ledgityVaultAdapter'
import { resolvePortalLedgityVaultConfigs } from '@/lib/portal/ledgity/ledgityVaultConfigStore'
import { parseHumanAmountToRaw } from '@/lib/portal/ledgity/ledgityVaultFormat'
import { buildLedgityLedgerMetadata } from '@/lib/portal/ledgity/ledgityLedgerMetadata'
import {
  assertLedgityWithdrawLiquidity,
  readLedgityVaultLiquidityMetrics,
  readLedgityWithdrawLiquidity,
} from '@/lib/portal/ledgity/ledgityVaultLiquidity'
import { assertLedgityWithdrawNotLocked } from '@/lib/portal/ledgity/ledgityVaultLock'
import { buildLedgityVaultTransactions } from '@/lib/portal/ledgity/ledgityVaultTx'
import { prepareLedgityTxSchema } from '@/lib/portal/ledgity/ledgityVaultValidation'
import {
  executeSandboxLedgityOperation,
  getSandboxMockVaultCatalog,
} from '@/lib/portal/ledgity/mocks/ledgityLocalSandbox'
import {
  assertNoConcurrentPendingGroup,
  assertWithdrawAmountWithinPosition,
  createMorphoLedgerEntries,
  MorphoVaultLedgerError,
} from '@/lib/portal/morphoVaultLedger'
import {
  ledgityRpcErrorResponse,
  morphoLedgerErrorResponse,
} from '@/lib/portal/portalVaultRouteHelpers'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
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
  return prepareLedgityTxSchema.parse({
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

/** Prépare la séquence de txs on-chain Ledgity (approve + deposit ERC4626, ou withdraw direct). */
export async function POST(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    await assertLedgityBetaAccess(personId)

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

    const configs = await resolvePortalLedgityVaultConfigs({ publishedOnly: true })
    const config = configs.find((row) => row.vaultAddress.toLowerCase() === vaultAddress.toLowerCase())
    if (!config) {
      return NextResponse.json({ error: 'Vault non publié.' }, { status: 404 })
    }
    if ((config.integrationMode as string) !== 'ledgity_vault') {
      return NextResponse.json({ error: 'Ce vault n’est pas en mode ledgity_vault.' }, { status: 400 })
    }

    const catalogRows = isLedgityLocalSandboxEnabled()
      ? (() => {
          const catalog = getSandboxMockVaultCatalog(vaultAddress)
          return catalog ? [catalog] : []
        })()
      : await fetchLedgityVaultCatalog({ addresses: [vaultAddress] })
    const catalogVault = catalogRows[0]
    const assetDecimals = catalogVault?.asset.decimals ?? 6
    const assetSymbol = catalogVault?.asset.symbol ?? 'USDC'
    const assetAddress = catalogVault?.asset.address ?? ''

    if (parsed.operation === 'deposit') {
      assertLedgityDepositsEnabled()
      await assertLedgityBetaDepositLimits({
        personId,
        amount: parsed.amount,
        assetDecimals,
      })
      await assertPortalVaultDepositTradingAvailable(parsed.amount)
    } else {
      assertLedgityWithdrawsEnabled()
    }

    const amountRaw = parseHumanAmountToRaw(parsed.amount, assetDecimals).toString()

    if (isLedgityLocalSandboxEnabled()) {
      return NextResponse.json(
        await executeSandboxLedgityOperation({
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

    if (!isLedgityVaultsEnabled()) {
      return NextResponse.json(
        {
          code: 'ledgity.deposits_disabled',
          message:
            'Les dépôts Ledgity live sont désactivés jusqu’à la fin de l’audit de sécurité. Utilisez le sandbox local en dev.',
        },
        { status: 503 },
      )
    }

    if (!assetAddress) {
      return NextResponse.json({ error: 'Actif sous-jacent introuvable pour ce vault.' }, { status: 502 })
    }

    let withdrawMode: 'instant' | 'async_request' = 'instant'
    if (parsed.operation === 'withdraw') {
      const lockState = await assertLedgityWithdrawNotLocked({ vaultAddress })
      withdrawMode = lockState.withdrawMode === 'async_request' ? 'async_request' : 'instant'

      const position = await fetchLedgityVaultPosition({ vaultAddress, walletAddress })
      const assetsInVault = position?.assets ?? '0'
      await assertWithdrawAmountWithinPosition({
        amountRaw: BigInt(amountRaw),
        assetsInVaultRaw: assetsInVault,
      })

      if (withdrawMode === 'instant') {
        const liquidity = await readLedgityWithdrawLiquidity({ vaultAddress, walletAddress })
        if (
          liquidity &&
          liquidity.maxWithdrawRaw > BigInt(0) &&
          liquidity.maxWithdrawRaw < BigInt(amountRaw)
        ) {
          withdrawMode = 'async_request'
        } else {
          await assertLedgityWithdrawLiquidity({
            vaultAddress,
            walletAddress,
            requestedAmountRaw: BigInt(amountRaw),
          })
        }
      }
    }

    const vaultMetrics = await readLedgityVaultLiquidityMetrics({ vaultAddress, chainId: LEDGITY_CHAIN_ID })
    const ppsAtTx = vaultMetrics?.pricePerShare != null ? String(vaultMetrics.pricePerShare) : null

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
        'ledgity.already_completed',
        'Cette opération a déjà été confirmée.',
        409,
      )
    }

    const transactions = await buildLedgityVaultTransactions({
      vaultAddress,
      assetAddress,
      walletAddress,
      operation: parsed.operation,
      amount: parsed.amount,
      assetDecimals,
      withdrawMode: parsed.operation === 'withdraw' ? withdrawMode : undefined,
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
            chainId: LEDGITY_CHAIN_ID,
            chainType: 'evm',
            walletAddress,
            privyWalletId: privyWalletIdFromBody,
            operation,
            amountRaw: operation === 'approve' ? '0' : amountRaw,
            assetSymbol,
            assetDecimals,
            idempotencyKey,
            integrationMode: 'ledgity_vault',
            txIndex: Math.max(0, txIndex),
            groupKey,
            metadataJson: buildLedgityLedgerMetadata({
              vaultAddress,
              assetSymbol,
              walletSource,
              ppsAtTx,
            }),
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
    const rpcResponse = ledgityRpcErrorResponse(error, 'ledgity.prepare')
    if (rpcResponse) return rpcResponse
    const ledgerResponse = morphoLedgerErrorResponse(error)
    if (ledgerResponse.status !== 500) return ledgerResponse
    console.error('[api/portal/ledgity/prepare POST]', error)
    const message = error instanceof Error ? error.message : 'Erreur interne.'
    return NextResponse.json({ code: 'ledgity.prepare_failed', message }, { status: 500 })
  }
}
