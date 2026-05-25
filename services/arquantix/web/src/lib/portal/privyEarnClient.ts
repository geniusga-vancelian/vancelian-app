import type {
  PortalEarnOperationPayload,
  PortalEarnVaultPosition,
  PortalEarnVaultsPayload,
  PortalEarnWalletAction,
} from '@/lib/portal/privyEarnTypes'
import { parsePortalExchangeError } from '@/lib/portal/parsePortalExchangeError'

async function earnFetch<T>(url: string, init?: RequestInit): Promise<T> {
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
    throw new Error(err.message)
  }
  return data as T
}

export async function fetchPortalEarnVaults(): Promise<PortalEarnVaultsPayload> {
  return earnFetch('/api/portal/privy/earn/vaults')
}

export async function fetchPortalEarnPosition(args: {
  vaultId: string
  privyWalletId: string
  walletAddress?: string | null
}): Promise<PortalEarnVaultPosition | null> {
  const params = new URLSearchParams({
    vault_id: args.vaultId,
    privy_wallet_id: args.privyWalletId,
  })
  if (args.walletAddress?.trim()) {
    params.set('wallet_address', args.walletAddress.trim())
  }
  const data = await earnFetch<{ position?: PortalEarnVaultPosition }>(
    `/api/portal/privy/earn/position?${params.toString()}`,
  )
  return data.position ?? null
}

export async function submitPortalEarnDeposit(args: {
  vaultId: string
  privyWalletId: string
  walletAddress?: string | null
  amount: string
  authorizationSignature?: string
  idempotencyKey?: string
  requestExpiry?: string
}): Promise<PortalEarnWalletAction> {
  const data = await earnFetch<PortalEarnOperationPayload>('/api/portal/privy/earn/deposit', {
    method: 'POST',
    body: JSON.stringify({
      vault_id: args.vaultId,
      privy_wallet_id: args.privyWalletId,
      wallet_address: args.walletAddress?.trim() || undefined,
      amount: args.amount,
      authorization_signature: args.authorizationSignature,
      idempotency_key: args.idempotencyKey,
      request_expiry: args.requestExpiry,
    }),
  })
  return data.action
}

export async function submitPortalEarnWithdraw(args: {
  vaultId: string
  privyWalletId: string
  walletAddress?: string | null
  amount: string
  authorizationSignature?: string
  idempotencyKey?: string
  requestExpiry?: string
}): Promise<PortalEarnWalletAction> {
  const data = await earnFetch<PortalEarnOperationPayload>('/api/portal/privy/earn/withdraw', {
    method: 'POST',
    body: JSON.stringify({
      vault_id: args.vaultId,
      privy_wallet_id: args.privyWalletId,
      wallet_address: args.walletAddress?.trim() || undefined,
      amount: args.amount,
      authorization_signature: args.authorizationSignature,
      idempotency_key: args.idempotencyKey,
      request_expiry: args.requestExpiry,
    }),
  })
  return data.action
}

export async function fetchPortalEarnActionStatus(args: {
  actionId: string
  privyWalletId: string
  walletAddress?: string | null
}): Promise<PortalEarnWalletAction> {
  const params = new URLSearchParams({ privy_wallet_id: args.privyWalletId })
  if (args.walletAddress?.trim()) {
    params.set('wallet_address', args.walletAddress.trim())
  }
  const data = await earnFetch<PortalEarnOperationPayload>(
    `/api/portal/privy/earn/actions/${encodeURIComponent(args.actionId)}?${params.toString()}`,
  )
  return data.action
}

const TERMINAL = new Set(['succeeded', 'failed', 'rejected'])

export async function pollPortalEarnAction(args: {
  actionId: string
  privyWalletId: string
  walletAddress?: string | null
  timeoutMs?: number
  intervalMs?: number
}): Promise<PortalEarnWalletAction> {
  const timeoutMs = args.timeoutMs ?? 180_000
  const intervalMs = args.intervalMs ?? 3_000
  const started = Date.now()
  let latest = await fetchPortalEarnActionStatus(args)
  while (!TERMINAL.has(latest.status) && Date.now() - started < timeoutMs) {
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
    latest = await fetchPortalEarnActionStatus(args)
  }
  return latest
}
