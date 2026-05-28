/**
 * Sync transaction_intents Morpho via API Python (observabilité — n’impacte pas le ledger).
 */
import { buildBackendUrl } from '@/lib/backend'

export type MorphoVaultTxIntentInput = {
  personId: string
  vaultTransactionId: string
  vaultAddress: string
  chainId: number
  walletAddress: string
  operation: string
  idempotencyKey: string
  txIndex: number
  txHash?: string | null
  vaultStatus?: string | null
}

function internalHeaders(): Record<string, string> {
  const key = process.env.TRANSACTION_INTENTS_INTERNAL_KEY?.trim()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (key) headers['X-Internal-Key'] = key
  return headers
}

async function postMorphoIntent(path: string, body: Record<string, unknown>): Promise<void> {
  try {
    const res = await fetch(buildBackendUrl(path), {
      method: 'POST',
      headers: internalHeaders(),
      body: JSON.stringify(body),
      cache: 'no-store',
    })
    if (!res.ok) {
      const text = await res.text()
      console.warn('[morphoIntentSync]', path, res.status, text)
    }
  } catch (error) {
    console.warn('[morphoIntentSync]', path, error)
  }
}

/** Après création ledger pending (prepare Morpho). */
export async function syncMorphoIntentPending(input: MorphoVaultTxIntentInput): Promise<void> {
  await postMorphoIntent('/api/internal/transaction-intents/morpho/pending', {
    person_id: input.personId,
    vault_transaction_id: input.vaultTransactionId,
    vault_address: input.vaultAddress,
    chain_id: input.chainId,
    wallet_address: input.walletAddress,
    operation: input.operation,
    idempotency_key: input.idempotencyKey,
    tx_index: input.txIndex,
    tx_hash: input.txHash ?? null,
    vault_status: input.vaultStatus ?? 'pending',
  })
}

/** Après confirm receipt (success / reverted / failed). */
export async function syncMorphoIntentAfterReceipt(args: {
  personId: string
  vaultTransactionId: string
  txHash?: string | null
  vaultStatus: string
}): Promise<void> {
  await postMorphoIntent('/api/internal/transaction-intents/morpho/receipt', {
    person_id: args.personId,
    vault_transaction_id: args.vaultTransactionId,
    tx_hash: args.txHash ?? null,
    vault_status: args.vaultStatus,
  })
}
