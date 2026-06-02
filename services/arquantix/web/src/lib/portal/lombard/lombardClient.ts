import type {
  LombardBorrowCapacity,
  LombardConfirmPayload,
  LombardMarketsPayload,
  LombardPreparePayload,
  LombardQuoteResult,
} from '@/lib/portal/lombard/lombardTypes'
import type { LombardPositionsPayload } from '@/lib/portal/lombard/lombardPositionTypes'
import { formatBaseRpcUserMessage, isBaseRpcTransientError } from '@/lib/blockchain/baseRpcErrors'
import type { LombardRetryPrepareContext } from '@/lib/portal/lombard/lombardRetryLinking'
import { buildLombardPrepareRetryBodyFields } from '@/lib/portal/lombard/lombardRetryLinking'
import { normalizeLombardBorrowAmountForApi } from '@/lib/portal/lombard/lombardBorrowUi'
import { parseLombardApiError } from '@/lib/portal/lombard/parseLombardApiError'
import type { WalletSourceMetadata } from '@/lib/wallet/executionWalletTypes'

async function lombardFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    credentials: 'include',
    cache: 'no-store',
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const message = parseLombardApiError(data, res.status)
    if (
      (typeof data === 'object' && data && (data as { code?: string }).code === 'lombard.base_rpc_busy') ||
      isBaseRpcTransientError(message)
    ) {
      throw new Error(formatBaseRpcUserMessage(message))
    }
    throw new Error(message)
  }
  return data as T
}

export async function fetchPortalLombardMarkets(): Promise<LombardMarketsPayload> {
  return lombardFetch('/api/portal/lombard/markets')
}

export async function fetchPortalLombardPositions(args: {
  walletAddress: string
}): Promise<LombardPositionsPayload> {
  const params = new URLSearchParams({ wallet_address: args.walletAddress })
  return lombardFetch(`/api/portal/lombard/position?${params.toString()}`)
}

export async function fetchPortalLombardBorrowCapacity(args: {
  collateral: string
  walletAddress: string
  targetLtvPercent: number
}): Promise<LombardBorrowCapacity> {
  const params = new URLSearchParams({
    collateral: args.collateral,
    wallet_address: args.walletAddress,
    target_ltv_percent: String(args.targetLtvPercent),
  })
  const data = await lombardFetch<{ capacity: LombardBorrowCapacity }>(
    `/api/portal/lombard/capacity?${params.toString()}`,
  )
  return data.capacity
}

export async function fetchPortalLombardQuote(args: {
  collateral: string
  borrowAmount: string
  walletAddress: string
  targetLtvPercent: number
}): Promise<LombardQuoteResult> {
  const borrowAmount = normalizeLombardBorrowAmountForApi(args.borrowAmount)
  if (!borrowAmount) {
    throw new Error('Montant emprunté invalide.')
  }
  const params = new URLSearchParams({
    collateral: args.collateral,
    borrow_amount: borrowAmount,
    wallet_address: args.walletAddress,
    target_ltv_percent: String(args.targetLtvPercent),
  })
  const data = await lombardFetch<{ quote: LombardQuoteResult }>(`/api/portal/lombard/quote?${params.toString()}`)
  return data.quote
}

export async function preparePortalLombardOpenLoan(args: {
  collateral: string
  borrowAmount: string
  walletAddress: string
  targetLtvPercent: number
  idempotencyKey: string
  walletSource?: WalletSourceMetadata
  externalWalletId?: string | null
  privyWalletId?: string | null
  retryLink?: LombardRetryPrepareContext | null
}): Promise<LombardPreparePayload> {
  const borrowAmount = normalizeLombardBorrowAmountForApi(args.borrowAmount)
  if (!borrowAmount) {
    throw new Error('Montant emprunté invalide.')
  }
  const retryBody = args.retryLink ? buildLombardPrepareRetryBodyFields(args.retryLink) : {}
  return lombardFetch('/api/portal/lombard/prepare', {
    method: 'POST',
    body: JSON.stringify({
      collateral: args.collateral,
      borrow_amount: borrowAmount,
      wallet_address: args.walletAddress,
      target_ltv_percent: args.targetLtvPercent,
      idempotency_key: args.idempotencyKey,
      wallet_source: args.walletSource?.wallet_source,
      external_wallet_id: args.externalWalletId,
      privy_wallet_id: args.privyWalletId,
      wallet_provider: args.walletSource?.wallet_provider,
      ...retryBody,
    }),
  })
}

export async function confirmPortalLombardTransactions(payload: LombardConfirmPayload): Promise<{
  results: Array<{
    ledgerEntryId: string
    txHash: string | null
    status: string
    blockNumber?: string | null
  }>
  confirmed: boolean
  failed: boolean
}> {
  return lombardFetch('/api/portal/lombard/confirm', {
    method: 'POST',
    body: JSON.stringify({
      group_key: payload.groupKey,
      results: payload.results.map((row) => ({
        ledger_entry_id: row.ledgerEntryId,
        tx_hash: row.txHash,
      })),
    }),
  })
}
