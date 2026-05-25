import type {
  PortalLedgityConfirmPayload,
  PortalLedgityPreparePayload,
  PortalLedgityVaultPosition,
  PortalLedgityVaultsPayload,
} from '@/lib/portal/ledgity/ledgityVaultTypes'
import { formatBaseRpcUserMessage, isBaseRpcTransientError } from '@/lib/blockchain/baseRpcErrors'
import { parsePortalExchangeError } from '@/lib/portal/parsePortalExchangeError'
import type { WalletSourceMetadata } from '@/lib/wallet/executionWalletTypes'

async function ledgityFetch<T>(url: string, init?: RequestInit): Promise<T> {
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
      (typeof data === 'object' && data && (data as { code?: string }).code === 'ledgity.base_rpc_busy') ||
      isBaseRpcTransientError(err.message)
    ) {
      throw new Error(formatBaseRpcUserMessage(err.message))
    }
    throw new Error(err.message)
  }
  return data as T
}

export async function fetchPortalLedgityVaults(): Promise<PortalLedgityVaultsPayload> {
  return ledgityFetch('/api/portal/ledgity/vaults')
}

export async function fetchPortalLedgityPosition(args: {
  vaultAddress: string
  walletAddress: string
}): Promise<PortalLedgityVaultPosition | null> {
  const params = new URLSearchParams({
    vault_address: args.vaultAddress,
    wallet_address: args.walletAddress,
  })
  const data = await ledgityFetch<{ position?: PortalLedgityVaultPosition | null }>(
    `/api/portal/ledgity/position?${params.toString()}`,
  )
  return data.position ?? null
}

export async function preparePortalLedgityTransactions(args: {
  vaultAddress: string
  walletAddress: string
  operation: 'deposit' | 'withdraw'
  amount: string
  idempotencyKey: string
  walletSource?: WalletSourceMetadata
  externalWalletId?: string | null
  privyWalletId?: string | null
}): Promise<PortalLedgityPreparePayload> {
  return ledgityFetch('/api/portal/ledgity/prepare', {
    method: 'POST',
    body: JSON.stringify({
      vault_address: args.vaultAddress,
      wallet_address: args.walletAddress,
      operation: args.operation,
      amount: args.amount,
      idempotency_key: args.idempotencyKey,
      wallet_source: args.walletSource?.wallet_source,
      external_wallet_id: args.externalWalletId,
      privy_wallet_id: args.privyWalletId,
      wallet_provider: args.walletSource?.wallet_provider,
    }),
  })
}

export async function confirmPortalLedgityTransactions(
  payload: PortalLedgityConfirmPayload,
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
  return ledgityFetch('/api/portal/ledgity/confirm', {
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
