/**
 * Client HTTP Privy côté serveur (Next BFF) — Earn / wallets.
 * Nécessite PRIVY_APP_ID + PRIVY_APP_SECRET (jamais exposés au client).
 */

import { PRIVY_EARN_API_BASE } from '@/lib/portal/privyEarnConfig'

export class PrivyServerApiError extends Error {
  readonly code: string
  readonly httpStatus: number

  constructor(code: string, message: string, httpStatus = 502) {
    super(message)
    this.code = code
    this.httpStatus = httpStatus
  }
}

export function isPrivyServerConfigured(): boolean {
  return Boolean(
    (process.env.PRIVY_APP_ID?.trim() || process.env.NEXT_PUBLIC_PRIVY_APP_ID?.trim()) &&
      process.env.PRIVY_APP_SECRET?.trim(),
  )
}

function privyCredentials(): { appId: string; authHeader: string } {
  const appId =
    process.env.PRIVY_APP_ID?.trim() || process.env.NEXT_PUBLIC_PRIVY_APP_ID?.trim() || ''
  const appSecret = process.env.PRIVY_APP_SECRET?.trim() || ''
  if (!appId || !appSecret) {
    throw new PrivyServerApiError(
      'privy.server.not_configured',
      'Configuration Privy serveur manquante (PRIVY_APP_ID / PRIVY_APP_SECRET).',
      503,
    )
  }
  const authHeader = `Basic ${Buffer.from(`${appId}:${appSecret}`).toString('base64')}`
  return { appId, authHeader }
}

type PrivyRequestOptions = {
  method?: 'GET' | 'POST'
  body?: unknown
  authorizationSignature?: string
  idempotencyKey?: string
  requestExpiry?: string
}

async function privyRequest<T>(path: string, options: PrivyRequestOptions = {}): Promise<T> {
  const { appId, authHeader } = privyCredentials()
  const headers: Record<string, string> = {
    Authorization: authHeader,
    'privy-app-id': appId,
    Accept: 'application/json',
    'User-Agent': 'arquantix-portal-earn/1.0',
  }
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (options.authorizationSignature?.trim()) {
    headers['privy-authorization-signature'] = options.authorizationSignature.trim()
  }
  if (options.idempotencyKey?.trim()) {
    headers['privy-idempotency-key'] = options.idempotencyKey.trim()
  }
  if (options.requestExpiry?.trim()) {
    headers['privy-request-expiry'] = options.requestExpiry.trim()
  }

  const res = await fetch(`${PRIVY_EARN_API_BASE}${path}`, {
    method: options.method ?? (options.body !== undefined ? 'POST' : 'GET'),
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: 'no-store',
    signal: AbortSignal.timeout(30_000),
  })

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const message =
      (data as { error?: string })?.error ||
      (data as { message?: string })?.message ||
      `Erreur Privy (HTTP ${res.status}).`
    throw new PrivyServerApiError('privy.server.request_failed', String(message), res.status)
  }
  return data as T
}

export async function fetchPrivyEarnVaultDetails(vaultId: string): Promise<Record<string, unknown>> {
  const encoded = encodeURIComponent(vaultId.trim())
  return privyRequest(`/v1/earn/ethereum/vaults/${encoded}`)
}

export async function fetchPrivyEarnVaultPosition(
  walletId: string,
  vaultId: string,
): Promise<Record<string, unknown>> {
  const wid = encodeURIComponent(walletId.trim())
  const vid = encodeURIComponent(vaultId.trim())
  return privyRequest(`/v1/wallets/${wid}/earn/ethereum/vaults?vault_id=${vid}`)
}

export async function postPrivyEarnDeposit(args: {
  walletId: string
  vaultId: string
  amount: string
  authorizationSignature?: string
  idempotencyKey?: string
  requestExpiry?: string
}): Promise<Record<string, unknown>> {
  const wid = encodeURIComponent(args.walletId.trim())
  return privyRequest(`/v1/wallets/${wid}/earn/ethereum/deposit`, {
    method: 'POST',
    body: { vault_id: args.vaultId.trim(), amount: args.amount.trim() },
    authorizationSignature: args.authorizationSignature,
    idempotencyKey: args.idempotencyKey,
    requestExpiry: args.requestExpiry,
  })
}

export async function postPrivyEarnWithdraw(args: {
  walletId: string
  vaultId: string
  amount: string
  authorizationSignature?: string
  idempotencyKey?: string
  requestExpiry?: string
}): Promise<Record<string, unknown>> {
  const wid = encodeURIComponent(args.walletId.trim())
  return privyRequest(`/v1/wallets/${wid}/earn/ethereum/withdraw`, {
    method: 'POST',
    body: { vault_id: args.vaultId.trim(), amount: args.amount.trim() },
    authorizationSignature: args.authorizationSignature,
    idempotencyKey: args.idempotencyKey,
    requestExpiry: args.requestExpiry,
  })
}

export async function fetchPrivyWalletAction(
  walletId: string,
  actionId: string,
): Promise<Record<string, unknown>> {
  const wid = encodeURIComponent(walletId.trim())
  const aid = encodeURIComponent(actionId.trim())
  return privyRequest(`/v1/wallets/${wid}/actions/${aid}`)
}
