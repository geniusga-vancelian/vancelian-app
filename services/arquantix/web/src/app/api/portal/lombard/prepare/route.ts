import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { isLombardV1Enabled } from '@/lib/portal/lombard/lombardConfig'
import { LombardAsyncTimeoutError, withLombardAsyncTimeout } from '@/lib/portal/lombard/lombardAsyncTimeout'
import { createLombardLedgerEntries, LombardLedgerError } from '@/lib/portal/lombard/lombardLedger'
import { LombardBetaError, LombardSafetyError } from '@/lib/portal/lombard/lombardBetaErrors'
import {
  logLombardOpsEvent,
  logLombardPrepareBlocked,
  logLombardPrepareStepSlow,
  logLombardPrepareSucceeded,
  logLombardQuotePrepareDrift,
} from '@/lib/portal/lombard/lombardOpsLog'
import { LombardMarketError, resolveLombardMarket } from '@/lib/portal/lombard/lombardMarket'
import { LombardQuoteError } from '@/lib/portal/lombard/lombardQuote'
import {
  isLombardQuotePrepareDriftCode,
  resolvePrepareBlockedDriftReason,
} from '@/lib/portal/lombard/lombardPrepareFailure'
import { logLombardSupportEvent } from '@/lib/portal/lombard/lombardSupportLog'
import { runLombardPreBorrowSafetyChecks } from '@/lib/portal/lombard/lombardSafetyChecks'
import { isLombardMockEnabled } from '@/lib/portal/lombard/lombardMockConfig'
import type { LombardRetryPrepareContext } from '@/lib/portal/lombard/lombardRetryLinking'
import { prepareLombardMockOpenLoan } from '@/lib/portal/lombard/mocks/lombardLocalMock'
import { assertLombardOpenLoanSimulates, LombardSimulationError } from '@/lib/portal/lombard/lombardOpenLoanSimulation'
import { buildLombardOpenLoanTransactions } from '@/lib/portal/lombard/lombardTx'
import { lombardPrepareSchema } from '@/lib/portal/lombard/lombardValidation'
import { isValidEvmAddress } from '@/lib/portal/morphoConstants'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
import {
  morphoLedgerErrorResponse,
  morphoRpcErrorResponse,
} from '@/lib/portal/portalVaultRouteHelpers'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
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
  return lombardPrepareSchema.parse({
    collateral: row.collateral,
    borrowAmount: row.borrow_amount ?? row.borrowAmount,
    walletAddress: row.wallet_address ?? row.walletAddress,
    idempotencyKey: row.idempotency_key ?? row.idempotencyKey,
    targetLtvPercent: row.target_ltv_percent ?? row.targetLtvPercent,
    portalWalletCollateralBalance:
      row.portal_wallet_collateral_balance ?? row.portalWalletCollateralBalance,
    logicalBorrowId: row.logical_borrow_id ?? row.logicalBorrowId,
    retryOfGroupKey: row.retry_of_group_key ?? row.retryOfGroupKey,
    retryAttemptNumber: row.retry_attempt_number ?? row.retryAttemptNumber,
  })
}

function buildRetryLinkFromParsed(
  parsed: z.infer<typeof lombardPrepareSchema>,
): LombardRetryPrepareContext | null {
  if (!parsed.logicalBorrowId) return null
  return {
    logicalBorrowId: parsed.logicalBorrowId,
    retryOfGroupKey: parsed.retryOfGroupKey ?? null,
    retryAttemptNumber: parsed.retryAttemptNumber ?? (parsed.retryOfGroupKey ? 1 : 0),
  }
}

/** Prépare approve + open loan (supply collateral + borrow USDC) via Morpho Blue. */
export async function POST(request: NextRequest) {
  let personId: string | null = null
  let parsed: z.infer<typeof lombardPrepareSchema> | null = null

  try {
    const auth = await requirePortalPersonId()
    if (auth instanceof NextResponse) return auth
    personId = auth

    if (!isLombardV1Enabled()) {
      return NextResponse.json({ code: 'lombard.disabled', message: 'Product unavailable.' }, { status: 503 })
    }

    const body = await request.json()
    parsed = parsePrepareBody(body)
    const walletSource = parseWalletSourceMetadata(body)
    const privyWalletIdFromBody = parsePrivyWalletIdFromBody(body)

    if (!isValidEvmAddress(parsed.walletAddress)) {
      return NextResponse.json({ error: 'Invalid wallet address.' }, { status: 400 })
    }

    await assertPortalWalletAddressOwnership({ personId, walletAddress: parsed.walletAddress })

    const requestPersonId = personId
    const requestParsed = parsed

    logLombardOpsEvent({
      code: 'lombard.prepare_requested',
      level: 'info',
      message: 'Lombard prepare requested.',
      personId: requestPersonId,
      walletAddress: requestParsed.walletAddress,
      groupKey: requestParsed.idempotencyKey,
      metadata: {
        collateral: requestParsed.collateral,
        borrowAmount: requestParsed.borrowAmount,
        targetLtvPercent: requestParsed.targetLtvPercent,
      },
    })

    const retryLink = buildRetryLinkFromParsed(requestParsed)
    const prepareStarted = Date.now()

    const safetyStarted = Date.now()
    const quote = await withLombardAsyncTimeout(
      'pre_borrow_safety_checks',
      () =>
        runLombardPreBorrowSafetyChecks({
          personId: requestPersonId,
          collateral: requestParsed.collateral,
          borrowAmount: requestParsed.borrowAmount,
          walletAddress: requestParsed.walletAddress,
          targetLtvPercent: requestParsed.targetLtvPercent,
          portalWalletCollateralBalance: requestParsed.portalWalletCollateralBalance,
          chainId: 8453,
        }),
      20_000,
    )
    const safetyMs = Date.now() - safetyStarted
    if (safetyMs > 5_000) {
      logLombardPrepareStepSlow({
        personId: requestPersonId,
        walletAddress: requestParsed.walletAddress,
        idempotencyKey: requestParsed.idempotencyKey,
        step: 'pre_borrow_safety_checks',
        durationMs: safetyMs,
      })
    }

    if (isLombardMockEnabled()) {
      const mockPrepared = await prepareLombardMockOpenLoan({
        personId: requestPersonId,
        collateral: requestParsed.collateral,
        borrowAmount: requestParsed.borrowAmount,
        walletAddress: requestParsed.walletAddress,
        idempotencyKey: requestParsed.idempotencyKey,
        quote,
        privyWalletId: privyWalletIdFromBody,
        walletMetadata: walletSource,
      })
      return NextResponse.json(mockPrepared)
    }

    const resolvedMarket = await withLombardAsyncTimeout(
      'resolve_lombard_market',
      () => resolveLombardMarket({ collateral: requestParsed.collateral }),
      18_000,
    )
    const buildStarted = Date.now()
    const transactions = await buildLombardOpenLoanTransactions({
      collateral: requestParsed.collateral,
      walletAddress: requestParsed.walletAddress,
      guaranteeAmountRaw: BigInt(quote.guaranteeAmountRaw),
      borrowAmountRaw: BigInt(quote.borrowAmountRaw),
      resolvedMarket,
    })
    const buildMs = Date.now() - buildStarted
    if (buildMs > 8_000) {
      logLombardPrepareStepSlow({
        personId: requestPersonId,
        walletAddress: requestParsed.walletAddress,
        idempotencyKey: requestParsed.idempotencyKey,
        step: 'build_open_loan_transactions',
        durationMs: buildMs,
      })
    }

    await assertLombardOpenLoanSimulates({
      walletAddress: requestParsed.walletAddress,
      transactions,
    })

    const ledgerEntries = await createLombardLedgerEntries({
      personId: requestPersonId,
      marketId: quote.marketId,
      walletAddress: requestParsed.walletAddress,
      privyWalletId: privyWalletIdFromBody,
      idempotencyKey: requestParsed.idempotencyKey,
      quote,
      transactions,
      walletMetadata: walletSource,
      retryLink,
    })

    logLombardPrepareSucceeded({
      personId: requestPersonId,
      walletAddress: requestParsed.walletAddress,
      collateral: requestParsed.collateral,
      borrowAmount: requestParsed.borrowAmount,
      idempotencyKey: requestParsed.idempotencyKey,
      durationMs: Date.now() - prepareStarted,
      txCount: transactions.length,
    })

    return NextResponse.json({
      transactions,
      ledgerEntries: ledgerEntries.map((row) => ({
        id: row.id,
        operation: row.operation,
        txIndex: row.txIndex,
      })),
      groupKey: requestParsed.idempotencyKey,
      idempotencyKey: requestParsed.idempotencyKey,
      logicalBorrowId: retryLink?.logicalBorrowId,
      quote,
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request data', issues: error.issues }, { status: 400 })
    }
    if (error instanceof LombardAsyncTimeoutError) {
      if (personId && parsed) {
        logLombardPrepareBlocked({
          personId,
          walletAddress: parsed.walletAddress,
          collateral: parsed.collateral,
          borrowAmount: parsed.borrowAmount,
          idempotencyKey: parsed.idempotencyKey,
          error: { code: error.code, message: error.message },
        })
      }
      return NextResponse.json({ code: error.code, message: error.message }, { status: 504 })
    }
    if (
      error instanceof LombardQuoteError ||
      error instanceof LombardMarketError ||
      error instanceof LombardBetaError ||
      error instanceof LombardSafetyError ||
      error instanceof LombardSimulationError
    ) {
      if (personId && parsed) {
        logLombardPrepareBlocked({
          personId,
          walletAddress: parsed.walletAddress,
          collateral: parsed.collateral,
          borrowAmount: parsed.borrowAmount,
          idempotencyKey: parsed.idempotencyKey,
          error: {
            code: error.code,
            message: error.message,
            ...(error instanceof LombardSimulationError && error.revertReason
              ? { revertReason: error.revertReason }
              : {}),
          },
        })
        if (isLombardQuotePrepareDriftCode(error.code)) {
          const driftReason = resolvePrepareBlockedDriftReason({
            errorCode: error.code,
            portalWalletCollateralBalance: parsed.portalWalletCollateralBalance,
          })
          logLombardQuotePrepareDrift({
            personId,
            walletAddress: parsed.walletAddress,
            collateral: parsed.collateral,
            borrowAmount: parsed.borrowAmount,
            idempotencyKey: parsed.idempotencyKey,
            errorCode: error.code,
            driftReason,
            portalWalletCollateralBalance: parsed.portalWalletCollateralBalance,
          })
          logLombardSupportEvent({
            code: 'lombard.quote_prepare_drift',
            level: driftReason === 'prepare_missing_portal_balance' ? 'critical' : 'warning',
            message: `Quote/prepare drift (${driftReason}): ${error.code}`,
            personId,
            walletAddress: parsed.walletAddress,
            metadata: {
              collateral: parsed.collateral,
              borrowAmount: parsed.borrowAmount,
              driftReason,
              portalBalanceSent: Boolean(parsed.portalWalletCollateralBalance?.trim()),
            },
          })
        }
      }
      return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
    }
    const rpcResponse = morphoRpcErrorResponse(error, 'lombard.prepare')
    if (rpcResponse) return rpcResponse
    const ledgerResponse = morphoLedgerErrorResponse(error)
    if (ledgerResponse.status !== 500) return ledgerResponse
    console.error('[api/portal/lombard/prepare POST]', error)
    const message = error instanceof Error ? error.message : 'Internal error.'
    return NextResponse.json({ code: 'lombard.prepare_failed', message }, { status: 500 })
  }
}
