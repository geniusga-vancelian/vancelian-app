/**
 * Sync transaction_intents Lombard via API Python (observabilité — n’impacte pas le ledger).
 */
import { buildBackendUrl } from '@/lib/backend'

export type LombardIntentStepInput = {
  step: 'approve' | 'authorize' | 'open_loan'
  txIndex: number
  ledgerEntryId: string
}

export type LombardConfirmIntentResult = {
  ledgerEntryId: string
  txHash?: string | null
  ledgerStatus: string
}

function internalHeaders(): Record<string, string> {
  const key = process.env.TRANSACTION_INTENTS_INTERNAL_KEY?.trim()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (key) headers['X-Internal-Key'] = key
  return headers
}

async function postLombardIntent(path: string, body: Record<string, unknown>): Promise<void> {
  try {
    const res = await fetch(buildBackendUrl(path), {
      method: 'POST',
      headers: internalHeaders(),
      body: JSON.stringify(body),
      cache: 'no-store',
    })
    if (!res.ok) {
      const text = await res.text()
      console.warn('[lombardIntentSync]', path, res.status, text)
    }
  } catch (error) {
    console.warn('[lombardIntentSync]', path, error)
  }
}

/** Après prepare Lombard (ledger group créé). */
export async function syncLombardIntentAfterPrepare(args: {
  personId: string
  groupKey: string
  marketId: string
  walletAddress: string
  chainId: number
  steps: LombardIntentStepInput[]
}): Promise<void> {
  await postLombardIntent('/api/internal/transaction-intents/lombard/prepare', {
    person_id: args.personId,
    group_key: args.groupKey,
    market_or_vault: args.marketId,
    wallet_address: args.walletAddress,
    chain_id: args.chainId,
    steps: args.steps.map((s) => ({
      step: s.step,
      tx_index: s.txIndex,
      ledger_entry_id: s.ledgerEntryId,
    })),
  })
}

/** Après confirm Lombard (batch receipts). */
export async function syncLombardIntentAfterConfirm(args: {
  personId: string
  groupKey: string
  marketId: string
  results: LombardConfirmIntentResult[]
}): Promise<void> {
  await postLombardIntent('/api/internal/transaction-intents/lombard/confirm', {
    person_id: args.personId,
    group_key: args.groupKey,
    market_or_vault: args.marketId,
    results: args.results.map((r) => ({
      ledger_entry_id: r.ledgerEntryId,
      tx_hash: r.txHash ?? null,
      ledger_status: r.ledgerStatus,
    })),
  })
}
