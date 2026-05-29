import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { morphoLedgerErrorResponse } from '@/lib/portal/portalVaultRouteHelpers'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
import { updateLedgerAfterReceipt } from '@/lib/portal/morphoVaultLedger'
import { assertMorphoUsdcBetaAccess } from '@/lib/portal/morphoUsdcBetaAccess'
import { idempotencyKeySchema } from '@/lib/portal/morphoVaultValidation'

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

/** Confirme les receipts on-chain et met à jour le ledger Morpho. */
export async function POST(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    await assertMorphoUsdcBetaAccess(personId)

    const parsed = parseConfirmBody(await request.json())
    if (!idempotencyKeySchema.safeParse(parsed.groupKey).success) {
      return NextResponse.json({ error: 'group_key invalide.' }, { status: 400 })
    }

    const updates = []
    for (const result of parsed.results) {
      const updated = await updateLedgerAfterReceipt({
        ledgerEntryId: result.ledgerEntryId,
        personId,
        txHash: result.txHash,
      })
      updates.push({
        ledgerEntryId: updated.id,
        txHash: updated.txHash,
        status: updated.status,
        blockNumber: updated.blockNumber?.toString() ?? null,
      })
    }

    const allSuccess = updates.every((row) => row.status === 'success')
    const anyReverted = updates.some((row) => row.status === 'reverted')

    return NextResponse.json({
      results: updates,
      confirmed: allSuccess,
      failed: anyReverted || updates.some((row) => row.status === 'failed'),
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request data', issues: error.issues }, { status: 400 })
    }
    const ledgerResponse = morphoLedgerErrorResponse(error)
    if (ledgerResponse.status !== 500) return ledgerResponse
    console.error('[api/portal/morpho/confirm POST]', error)
    return NextResponse.json({ code: 'morpho.confirm_failed', message: 'Erreur interne.' }, { status: 500 })
  }
}
