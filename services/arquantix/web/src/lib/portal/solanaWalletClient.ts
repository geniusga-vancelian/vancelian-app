export type SolanaWalletPayload = {
  chain_type: 'solana'
  address: string
  wallet_id: string
  created: boolean
  person_wallet_id: string
}

export type SolanaWalletStatusPayload = {
  status: 'missing' | 'unlinked' | 'linked'
  chain_type: 'solana'
  address?: string
  wallet_id?: string
  person_wallet_id?: string
  created: boolean
}

export type SolanaWalletUiState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'missing' }
  | { status: 'unlinked'; address: string; walletId: string }
  | { status: 'ready'; wallet: SolanaWalletPayload }
  | { status: 'error'; message: string }

export function parseSolanaWalletPayload(data: unknown): SolanaWalletPayload | null {
  if (!data || typeof data !== 'object') return null
  const row = data as Record<string, unknown>
  const address = typeof row.address === 'string' ? row.address.trim() : ''
  const walletId = typeof row.wallet_id === 'string' ? row.wallet_id.trim() : ''
  const personWalletId =
    typeof row.person_wallet_id === 'string' ? row.person_wallet_id.trim() : ''
  if (!address || !walletId || !personWalletId) return null
  return {
    chain_type: 'solana',
    address,
    wallet_id: walletId,
    created: row.created === true,
    person_wallet_id: personWalletId,
  }
}

export function parseSolanaWalletStatus(data: unknown): SolanaWalletStatusPayload | null {
  if (!data || typeof data !== 'object') return null
  const row = data as Record<string, unknown>
  const status = row.status
  if (status !== 'missing' && status !== 'unlinked' && status !== 'linked') return null
  const address = typeof row.address === 'string' ? row.address.trim() : undefined
  const walletId = typeof row.wallet_id === 'string' ? row.wallet_id.trim() : undefined
  const personWalletId =
    typeof row.person_wallet_id === 'string' ? row.person_wallet_id.trim() : undefined
  return {
    status,
    chain_type: 'solana',
    address: address || undefined,
    wallet_id: walletId || undefined,
    person_wallet_id: personWalletId || undefined,
    created: row.created === true,
  }
}

export function resolveSolanaWalletUiState(args: {
  loading: boolean
  error: string
  walletStatus: SolanaWalletStatusPayload | null
}): SolanaWalletUiState {
  if (args.loading) return { status: 'loading' }
  if (args.error) return { status: 'error', message: args.error }
  if (!args.walletStatus) return { status: 'missing' }

  if (args.walletStatus.status === 'linked') {
    const wallet = parseSolanaWalletPayload(args.walletStatus)
    if (wallet) return { status: 'ready', wallet }
    return { status: 'error', message: 'Invalid linked Solana wallet response.' }
  }

  if (args.walletStatus.status === 'unlinked') {
    const address = args.walletStatus.address?.trim() ?? ''
    const walletId = args.walletStatus.wallet_id?.trim() ?? ''
    if (!address) {
      return { status: 'error', message: 'Invalid unlinked Solana wallet response.' }
    }
    return { status: 'unlinked', address, walletId: walletId || address }
  }

  return { status: 'missing' }
}

export function resolveSolanaExplorerAddressUrl(address: string): string {
  const trimmed = address.trim()
  if (!trimmed) return 'https://solscan.io'
  return `https://solscan.io/account/${encodeURIComponent(trimmed)}`
}

function extractPortalApiError(data: unknown, fallback: string): string {
  if (!data || typeof data !== 'object') return fallback
  const row = data as Record<string, unknown>
  if (typeof row.error === 'string' && row.error.trim()) return row.error

  const detail = row.detail
  if (typeof detail === 'string' && detail.trim()) {
    if (detail === 'Not Found') {
      return 'Wallet service unavailable. Redeploy or restart the backend API, then retry.'
    }
    return detail
  }
  if (detail && typeof detail === 'object') {
    const structured = detail as Record<string, unknown>
    if (typeof structured.message === 'string' && structured.message.trim()) {
      return structured.message
    }
  }
  return fallback
}

export async function fetchPortalSolanaWalletStatus(): Promise<SolanaWalletStatusPayload> {
  const res = await fetch('/api/portal/wallets/solana', {
    credentials: 'include',
    cache: 'no-store',
  })
  const data = await res.json().catch(() => ({}))
  if (res.status === 401) {
    throw new Error('Session expired. Please sign in again.')
  }
  if (!res.ok) {
    throw new Error(extractPortalApiError(data, 'Unable to load Solana wallet.'))
  }
  const status = parseSolanaWalletStatus(data)
  if (!status) throw new Error('Invalid Solana wallet status response.')
  return status
}

export async function createPortalSolanaWallet(): Promise<SolanaWalletPayload> {
  const res = await fetch('/api/portal/wallets/solana/create', {
    method: 'POST',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
  const data = await res.json().catch(() => ({}))
  if (res.status === 401) {
    throw new Error('Session expired. Please sign in again.')
  }
  if (!res.ok) {
    throw new Error(extractPortalApiError(data, 'Unable to create Solana wallet.'))
  }
  const wallet = parseSolanaWalletPayload(data)
  if (!wallet) throw new Error('Invalid Solana wallet response.')
  return wallet
}
