import { parsePortalExchangeError } from '@/lib/portal/parsePortalExchangeError'
import type { ExternalWalletConnector, VerifiedExternalWallet } from '@/lib/wallet/executionWalletTypes'

export type ExternalWalletNoncePayload = {
  nonce: string
  message: string
  expiresAt: string
}

export async function fetchExternalWalletNonce(): Promise<ExternalWalletNoncePayload> {
  const res = await fetch('/api/portal/wallets/external/nonce', {
    method: 'POST',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = parsePortalExchangeError(data)
    throw new Error(err.message)
  }
  return data as ExternalWalletNoncePayload
}

export async function verifyExternalWalletLink(args: {
  walletAddress: string
  signature: `0x${string}`
  nonce: string
  walletProvider: ExternalWalletConnector
  chainId?: number
}): Promise<VerifiedExternalWallet> {
  const res = await fetch('/api/portal/wallets/external/verify', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      wallet_address: args.walletAddress,
      signature: args.signature,
      nonce: args.nonce,
      wallet_provider: args.walletProvider,
      chain_id: args.chainId,
    }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = parsePortalExchangeError(data)
    throw new Error(err.message)
  }
  return data.wallet as VerifiedExternalWallet
}

export async function fetchVerifiedExternalWallets(): Promise<VerifiedExternalWallet[]> {
  const res = await fetch('/api/portal/wallets/external', {
    credentials: 'include',
    cache: 'no-store',
  })
  const data = await res.json().catch(() => ({}))
  if (res.status === 401) {
    throw new Error('Session expirée. Reconnectez-vous.')
  }
  if (!res.ok) {
    const err = parsePortalExchangeError(data)
    throw new Error(err.message)
  }
  return Array.isArray(data.wallets) ? (data.wallets as VerifiedExternalWallet[]) : []
}

export async function unlinkExternalWallet(walletId: string): Promise<void> {
  const res = await fetch(`/api/portal/wallets/external/${encodeURIComponent(walletId)}`, {
    method: 'DELETE',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = parsePortalExchangeError(data)
    throw new Error(err.message)
  }
}

export type ExternalWalletMockStatus = {
  mockEnabled: boolean
  devRouteAvailable: boolean
  session: { authenticated: boolean; personId: string | null }
  linked: boolean
  wallet: VerifiedExternalWallet | null
}

export async function fetchExternalWalletMockStatus(): Promise<ExternalWalletMockStatus> {
  const res = await fetch('/api/dev/external-wallet-mock/status', {
    credentials: 'include',
    cache: 'no-store',
  })
  const data = await res.json().catch(() => ({}))
  if (res.status === 403) {
    return {
      mockEnabled: false,
      devRouteAvailable: false,
      session: { authenticated: false, personId: null },
      linked: false,
      wallet: null,
    }
  }
  if (!res.ok) {
    const err = parsePortalExchangeError(data)
    throw new Error(err.message)
  }
  return data as ExternalWalletMockStatus
}

export async function linkLocalMockExternalWalletDev(): Promise<VerifiedExternalWallet> {
  const res = await fetch('/api/dev/external-wallet-mock/link', {
    method: 'POST',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = parsePortalExchangeError(data)
    throw new Error(err.message)
  }
  return data.wallet as VerifiedExternalWallet
}

export async function unlinkLocalMockExternalWalletDev(): Promise<void> {
  const res = await fetch('/api/dev/external-wallet-mock/unlink', {
    method: 'DELETE',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = parsePortalExchangeError(data)
    throw new Error(err.message)
  }
}
