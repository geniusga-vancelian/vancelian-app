import type {
  PortalMorphoConfirmPayload,
  PortalMorphoPreparePayload,
  PortalMorphoVaultPosition,
  PortalMorphoVaultsPayload,
} from '@/lib/portal/morphoVaultTypes'
import { formatBaseRpcUserMessage, isBaseRpcTransientError } from '@/lib/blockchain/baseRpcErrors'
import { parsePortalExchangeError } from '@/lib/portal/parsePortalExchangeError'

async function morphoFetch<T>(url: string, init?: RequestInit): Promise<T> {
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
    const err = parsePortalExchangeError(data)
    if (
      (typeof data === 'object' && data && (data as { code?: string }).code === 'morpho.base_rpc_busy') ||
      isBaseRpcTransientError(err.message)
    ) {
      throw new Error(formatBaseRpcUserMessage(err.message))
    }
    throw new Error(err.message)
  }
  return data as T
}

export async function fetchPortalMorphoVaults(): Promise<PortalMorphoVaultsPayload> {
  return morphoFetch('/api/portal/morpho/vaults')
}

export async function fetchPortalMorphoPosition(args: {
  vaultAddress: string
  walletAddress: string
}): Promise<PortalMorphoVaultPosition | null> {
  const params = new URLSearchParams({
    vault_address: args.vaultAddress,
    wallet_address: args.walletAddress,
  })
  const data = await morphoFetch<{ position?: PortalMorphoVaultPosition | null }>(
    `/api/portal/morpho/position?${params.toString()}`,
  )
  return data.position ?? null
}

export async function preparePortalMorphoTransactions(args: {
  vaultAddress: string
  walletAddress: string
  operation: 'deposit' | 'withdraw'
  amount: string
  idempotencyKey: string
}): Promise<PortalMorphoPreparePayload> {
  return morphoFetch('/api/portal/morpho/prepare', {
    method: 'POST',
    body: JSON.stringify({
      vault_address: args.vaultAddress,
      wallet_address: args.walletAddress,
      operation: args.operation,
      amount: args.amount,
      idempotency_key: args.idempotencyKey,
    }),
  })
}

export async function confirmPortalMorphoTransactions(
  payload: PortalMorphoConfirmPayload,
): Promise<{
  results: Array<{
    ledgerEntryId: string
    txHash: string | null
    status: string
    blockNumber?: string | null
  }>
  confirmed: boolean
  failed: boolean
}> {
  return morphoFetch('/api/portal/morpho/confirm', {
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
