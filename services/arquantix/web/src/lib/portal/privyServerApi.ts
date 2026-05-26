import { getPrivyAppIdServer } from '@/lib/portal/privyConfig'
import {
  buildPrivyEthSendTransactionRpcBody,
  buildPrivyWalletRpcUrl,
} from '@/lib/portal/privySponsoredRpcRequest'
import { normalizeTxHash } from '@/lib/portal/swapTxFormat'

export class PrivyServerApiError extends Error {
  readonly code: string
  readonly httpStatus?: number

  constructor(code: string, message: string, httpStatus?: number) {
    super(message)
    this.name = 'PrivyServerApiError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

function readPrivyAppSecret(): string {
  return process.env.PRIVY_APP_SECRET?.trim() || ''
}

export function privyServerApiConfigured(): boolean {
  return Boolean(getPrivyAppIdServer() && readPrivyAppSecret())
}

function buildPrivyAuthHeaders(): Record<string, string> {
  const appId = getPrivyAppIdServer()
  const appSecret = readPrivyAppSecret()
  if (!appId || !appSecret) {
    throw new PrivyServerApiError(
      'privy.server_not_configured',
      'Privy serveur non configuré (PRIVY_APP_ID / PRIVY_APP_SECRET).',
    )
  }
  const auth = Buffer.from(`${appId}:${appSecret}`).toString('base64')
  return {
    Authorization: `Basic ${auth}`,
    'privy-app-id': appId,
    Accept: 'application/json',
    'Content-Type': 'application/json',
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function normalizeHash(value: string): string {
  return normalizeTxHash(value.trim())
}

function readPrivyErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object') return fallback
  const row = payload as Record<string, unknown>
  const error = row.error
  if (typeof error === 'string' && error.trim()) return error.trim()
  if (error && typeof error === 'object') {
    const nested = error as Record<string, unknown>
    if (typeof nested.message === 'string' && nested.message.trim()) return nested.message.trim()
  }
  if (typeof row.message === 'string' && row.message.trim()) return row.message.trim()
  return fallback
}

function readRpcHash(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') return null
  const row = payload as Record<string, unknown>
  const data = row.data
  if (!data || typeof data !== 'object') return null
  const nested = data as Record<string, unknown>
  for (const key of ['hash', 'transaction_hash', 'tx_hash']) {
    const value = nested[key]
    if (typeof value === 'string' && value.trim() && value.trim() !== '0x') {
      return normalizeHash(value)
    }
  }
  return null
}

function readRpcTransactionId(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') return null
  const data = (payload as Record<string, unknown>).data
  if (!data || typeof data !== 'object') return null
  const id = (data as Record<string, unknown>).transaction_id
  return typeof id === 'string' && id.trim() ? id.trim() : null
}

async function fetchPrivyTransactionHash(transactionId: string): Promise<string | null> {
  const headers = buildPrivyAuthHeaders()
  const res = await fetch(`https://api.privy.io/v1/transactions/${encodeURIComponent(transactionId)}`, {
    method: 'GET',
    headers,
    cache: 'no-store',
    signal: AbortSignal.timeout(20_000),
  })
  const payload = await res.json().catch(() => null)
  if (!res.ok) return null

  if (!payload || typeof payload !== 'object') return null
  const row = payload as Record<string, unknown>
  for (const key of ['transaction_hash', 'hash', 'tx_hash']) {
    const value = row[key]
    if (typeof value === 'string' && value.trim() && value.trim() !== '0x') {
      return normalizeHash(value)
    }
  }
  const nested = row.data
  if (nested && typeof nested === 'object') {
    for (const key of ['transaction_hash', 'hash', 'tx_hash']) {
      const value = (nested as Record<string, unknown>)[key]
      if (typeof value === 'string' && value.trim() && value.trim() !== '0x') {
        return normalizeHash(value)
      }
    }
  }
  return null
}

async function waitForPrivyTransactionHash(transactionId: string): Promise<string> {
  const started = Date.now()
  while (Date.now() - started < 120_000) {
    const hash = await fetchPrivyTransactionHash(transactionId)
    if (hash) return hash
    await sleep(2_000)
  }
  throw new PrivyServerApiError(
    'privy.tx_hash_timeout',
    'Transaction Privy sponsorisée en cours — hash indisponible. Réessayez dans quelques instants.',
  )
}

export async function sendPrivySponsoredEthereumTransaction(args: {
  privyWalletId: string
  authorizationSignature: string
  chainId: number
  to: string
  data: string
  value?: string | number | bigint
  gasLimit?: string | number | bigint
}): Promise<{ hash: string; transactionId?: string | null }> {
  const walletId = args.privyWalletId.trim()
  if (!walletId) {
    throw new PrivyServerApiError('privy.wallet_id_required', 'Wallet Privy introuvable pour cette session.')
  }

  const authorizationSignature = args.authorizationSignature.trim()
  if (!authorizationSignature) {
    throw new PrivyServerApiError(
      'privy.authorization_signature_required',
      'Signature d’autorisation Privy manquante.',
      400,
    )
  }

  const rpcBody = buildPrivyEthSendTransactionRpcBody({
    chainId: args.chainId,
    to: args.to,
    data: args.data,
    value: args.value,
    gasLimit: args.gasLimit,
  })

  const headers = {
    ...buildPrivyAuthHeaders(),
    'privy-authorization-signature': authorizationSignature,
  }
  const res = await fetch(buildPrivyWalletRpcUrl(walletId), {
    method: 'POST',
    headers,
    body: JSON.stringify(rpcBody),
    cache: 'no-store',
    signal: AbortSignal.timeout(60_000),
  })

  const payload = await res.json().catch(() => null)
  if (!res.ok) {
    throw new PrivyServerApiError(
      'privy.rpc_failed',
      readPrivyErrorMessage(payload, `Envoi transaction Privy impossible (HTTP ${res.status}).`),
      res.status,
    )
  }

  let hash = readRpcHash(payload)
  const transactionId = readRpcTransactionId(payload)
  if (!hash && transactionId) {
    hash = await waitForPrivyTransactionHash(transactionId)
  }
  if (!hash) {
    throw new PrivyServerApiError(
      'privy.missing_tx_hash',
      'Transaction Privy envoyée mais hash indisponible — réessayez.',
    )
  }

  return { hash, transactionId }
}
