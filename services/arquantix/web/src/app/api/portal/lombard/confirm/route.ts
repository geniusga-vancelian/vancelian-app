import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { isLombardV1Enabled } from '@/lib/portal/lombard/lombardConfig'
import { isLombardMockEnabled } from '@/lib/portal/lombard/lombardMockConfig'
import {
  reconcileLombardMockOpenLoanGroup,
} from '@/lib/portal/lombard/mocks/lombardLocalMock'
import { reconcileLombardOpenLoanGroup } from '@/lib/portal/lombard/lombardReconciliation'
import { logLombardOpsEvent } from '@/lib/portal/lombard/lombardOpsLog'
import { creditLombardMockBorrowToPrivyLedger } from '@/lib/portal/lombard/lombardMockPrivyLedgerCredit'
import { syncLombardIntentAfterConfirm } from '@/lib/portal/lombard/lombardIntentSync'
import { updateLedgerAfterReceipt } from '@/lib/portal/morphoVaultLedger'
import { idempotencyKeySchema } from '@/lib/portal/lombard/lombardValidation'
import {
  morphoLedgerErrorResponse,
  requirePortalPersonId,
} from '@/lib/portal/portalWalletRouteHelpers'

const confirmSchema = z.object({
  groupKey: z.string().trim().min(8).max(128),
  results: z
    .array(
      z.object({
        ledgerEntryId: z.string().trim().min(1),
        txHash: z.string().trim().regex(/^0x[0-9a-fA-F]{64}$/),
      }),
    )
    .min(1),
})

function parseConfirmBody(body: unknown) {
  if (!body || typeof body !== 'object') {
    throw new z.ZodError([])
  }
  const row = body as Record<string, unknown>
  return confirmSchema.parse({
    groupKey: row.group_key ?? row.groupKey,
    results: (row.results as unknown[])?.map((item) => {
      const entry = item as Record<string, unknown>
      return {
        ledgerEntryId: entry.ledger_entry_id ?? entry.ledgerEntryId,
        txHash: entry.tx_hash ?? entry.txHash,
      }
    }),
  })
}

/** Confirme les receipts on-chain pour une ouverture d'emprunt Lombard. */
export async function POST(request: NextRequest) {
  let personId: string | null = null

  try {
    const auth = await requirePortalPersonId()
    if (auth instanceof NextResponse) return auth
    personId = auth

    if (!isLombardV1Enabled()) {
      return NextResponse.json({ code: 'lombard.disabled', message: 'Product unavailable.' }, { status: 503 })
    }

    const parsed = parseConfirmBody(await request.json())
    if (!idempotencyKeySchema.safeParse(parsed.groupKey).success) {
      return NextResponse.json({ error: 'Invalid group_key.' }, { status: 400 })
    }

    for (const result of parsed.results) {
      logLombardOpsEvent({
        code: 'lombard.tx_submitted',
        level: 'info',
        message: 'Lombard transaction submitted for confirmation.',
        personId,
        groupKey: parsed.groupKey,
        ledgerEntryId: result.ledgerEntryId,
        txHash: result.txHash,
      })
    }

    const updates = []
    let marketId = ''
    for (const result of parsed.results) {
      const updated = await updateLedgerAfterReceipt({
        ledgerEntryId: result.ledgerEntryId,
        personId,
        txHash: result.txHash,
      })
      if (!marketId) marketId = updated.vaultAddress
      updates.push({
        ledgerEntryId: updated.id,
        txHash: updated.txHash,
        status: updated.status,
        blockNumber: updated.blockNumber?.toString() ?? null,
      })
    }

    const allSuccess = updates.every((row) => row.status === 'success')
    const anyReverted = updates.some((row) => row.status === 'reverted')
    const anyFailed = updates.some((row) => row.status === 'failed')

    let reconciliation = null
    if (allSuccess) {
      reconciliation = isLombardMockEnabled()
        ? await reconcileLombardMockOpenLoanGroup({
            personId,
            groupKey: parsed.groupKey,
          })
        : await reconcileLombardOpenLoanGroup({
            personId,
            groupKey: parsed.groupKey,
          })
      if (isLombardMockEnabled()) {
        try {
          await creditLombardMockBorrowToPrivyLedger({
            personId,
            groupKey: parsed.groupKey,
          })
        } catch (creditError) {
          console.warn('[api/portal/lombard/confirm POST] mock USDC ledger credit failed:', creditError)
        }
      }
      logLombardOpsEvent({
        code: 'lombard.confirm_success',
        level: 'info',
        message: 'Lombard open loan confirmed.',
        personId,
        groupKey: parsed.groupKey,
        metadata: {
          txCount: updates.length,
          reconciliationStatus: reconciliation?.status ?? null,
        },
      })
    } else {
      logLombardOpsEvent({
        code: 'lombard.confirm_failed',
        level: 'error',
        message: 'Lombard open loan confirmation failed.',
        personId,
        groupKey: parsed.groupKey,
        metadata: {
          txCount: updates.length,
          anyReverted,
          anyFailed,
          statuses: updates.map((row) => row.status),
        },
      })
    }

    void syncLombardIntentAfterConfirm({
      personId,
      groupKey: parsed.groupKey,
      marketId,
      results: updates.map((row) => ({
        ledgerEntryId: row.ledgerEntryId,
        txHash: row.txHash,
        ledgerStatus: row.status,
      })),
    })

    return NextResponse.json({
      results: updates,
      confirmed: allSuccess,
      failed: anyReverted || anyFailed,
      reconciliation,
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request data', issues: error.issues }, { status: 400 })
    }
    const ledgerResponse = morphoLedgerErrorResponse(error)
    if (ledgerResponse.status !== 500) return ledgerResponse
    console.error('[api/portal/lombard/confirm POST]', error)
    return NextResponse.json({ code: 'lombard.confirm_failed', message: 'Internal error.' }, { status: 500 })
  }
}
