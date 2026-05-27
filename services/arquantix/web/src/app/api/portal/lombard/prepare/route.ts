import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { isLombardV1Enabled } from '@/lib/portal/lombard/lombardConfig'
import { createLombardLedgerEntries, LombardLedgerError } from '@/lib/portal/lombard/lombardLedger'
import { LombardBetaError, LombardSafetyError } from '@/lib/portal/lombard/lombardBetaErrors'
import { logLombardOpsEvent, logLombardPrepareBlocked } from '@/lib/portal/lombard/lombardOpsLog'
import { LombardMarketError } from '@/lib/portal/lombard/lombardMarket'
import { LombardQuoteError } from '@/lib/portal/lombard/lombardQuote'
import { runLombardPreBorrowSafetyChecks } from '@/lib/portal/lombard/lombardSafetyChecks'
import { isLombardMockEnabled } from '@/lib/portal/lombard/lombardMockConfig'
import { prepareLombardMockOpenLoan } from '@/lib/portal/lombard/mocks/lombardLocalMock'
import { buildLombardOpenLoanTransactions } from '@/lib/portal/lombard/lombardTx'
import { lombardPrepareSchema } from '@/lib/portal/lombard/lombardValidation'
import { isValidEvmAddress } from '@/lib/portal/morphoConstants'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
import {
  morphoLedgerErrorResponse,
  morphoRpcErrorResponse,
  requirePortalPersonId,
} from '@/lib/portal/portalWalletRouteHelpers'
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
  })
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

    logLombardOpsEvent({
      code: 'lombard.prepare_requested',
      level: 'info',
      message: 'Lombard prepare requested.',
      personId,
      walletAddress: parsed.walletAddress,
      groupKey: parsed.idempotencyKey,
      metadata: {
        collateral: parsed.collateral,
        borrowAmount: parsed.borrowAmount,
        targetLtvPercent: parsed.targetLtvPercent,
      },
    })

    const quote = await runLombardPreBorrowSafetyChecks({
      personId,
      collateral: parsed.collateral,
      borrowAmount: parsed.borrowAmount,
      walletAddress: parsed.walletAddress,
      targetLtvPercent: parsed.targetLtvPercent,
      chainId: 8453,
    })

    if (isLombardMockEnabled()) {
      const mockPrepared = await prepareLombardMockOpenLoan({
        personId,
        collateral: parsed.collateral,
        borrowAmount: parsed.borrowAmount,
        walletAddress: parsed.walletAddress,
        idempotencyKey: parsed.idempotencyKey,
        quote,
        privyWalletId: privyWalletIdFromBody,
        walletMetadata: walletSource,
      })
      return NextResponse.json(mockPrepared)
    }

    const transactions = await buildLombardOpenLoanTransactions({
      collateral: parsed.collateral,
      walletAddress: parsed.walletAddress,
      guaranteeAmountRaw: BigInt(quote.guaranteeAmountRaw),
      borrowAmountRaw: BigInt(quote.borrowAmountRaw),
    })

    const ledgerEntries = await createLombardLedgerEntries({
      personId,
      marketId: quote.marketId,
      walletAddress: parsed.walletAddress,
      privyWalletId: privyWalletIdFromBody,
      idempotencyKey: parsed.idempotencyKey,
      quote,
      transactions,
      walletMetadata: walletSource,
    })

    return NextResponse.json({
      transactions,
      ledgerEntries: ledgerEntries.map((row) => ({
        id: row.id,
        operation: row.operation,
        txIndex: row.txIndex,
      })),
      groupKey: parsed.idempotencyKey,
      idempotencyKey: parsed.idempotencyKey,
      quote,
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request data', issues: error.issues }, { status: 400 })
    }
    if (
      error instanceof LombardQuoteError ||
      error instanceof LombardMarketError ||
      error instanceof LombardBetaError ||
      error instanceof LombardSafetyError
    ) {
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
