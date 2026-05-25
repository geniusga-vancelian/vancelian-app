import { parsePortalExchangeError } from '@/lib/portal/parsePortalExchangeError'
import { readPortalCache, writePortalCache } from '@/lib/portal/portalClientCache'

export type PortalPersonCryptoWallet = {
  id: string
  address: string
  chain_type: string
  chain_id?: number | null
  wallet_type: string
  provider: string
  is_primary: boolean
}

export type PrivyExchangeWalletPayload = {
  address: string
  chain_type: 'evm'
  chain_id?: number
  wallet_type: string
  privy_wallet_id?: string
}

function parsePersonWallets(data: unknown): PortalPersonCryptoWallet[] {
  if (!data || typeof data !== 'object') return []
  const wallets = (data as { wallets?: unknown }).wallets
  if (!Array.isArray(wallets)) return []
  const out: PortalPersonCryptoWallet[] = []
  for (const row of wallets) {
    if (!row || typeof row !== 'object') continue
    const w = row as Record<string, unknown>
    const id = typeof w.id === 'string' ? w.id : ''
    const address = typeof w.address === 'string' ? w.address : ''
    if (!id || !address) continue
    out.push({
      id,
      address,
      chain_type: typeof w.chain_type === 'string' ? w.chain_type : 'evm',
      chain_id: typeof w.chain_id === 'number' ? w.chain_id : null,
      wallet_type: typeof w.wallet_type === 'string' ? w.wallet_type : 'embedded',
      provider: typeof w.provider === 'string' ? w.provider : 'privy',
      is_primary: w.is_primary === true,
    })
  }
  return out
}

export function parseCaip2ChainId(chainId: string | undefined): number | undefined {
  const raw = (chainId || '').trim()
  const match = /^eip155:(\d+)$/.exec(raw)
  if (!match) return undefined
  const parsed = Number.parseInt(match[1], 10)
  return Number.isFinite(parsed) ? parsed : undefined
}

export function toPrivyExchangeWalletPayload(input: {
  address: string
  chainId?: string
  walletType?: string
  privyWalletId?: string | null
}): PrivyExchangeWalletPayload {
  const payload: PrivyExchangeWalletPayload = {
    address: input.address.trim(),
    chain_type: 'evm',
    chain_id: parseCaip2ChainId(input.chainId) ?? 1,
    wallet_type: (input.walletType || 'embedded').trim() || 'embedded',
  }
  const privyWalletId = input.privyWalletId?.trim()
  if (privyWalletId) {
    payload.privy_wallet_id = privyWalletId
  }
  return payload
}

export function resolvePrimaryPersonCryptoWallet(
  wallets: PortalPersonCryptoWallet[],
): PortalPersonCryptoWallet | null {
  if (wallets.length === 0) return null
  return wallets.find((w) => w.is_primary) ?? wallets[0] ?? null
}

export function findEvmPersonWallet(
  wallets: PortalPersonCryptoWallet[],
): PortalPersonCryptoWallet | null {
  const evmWallets = wallets.filter((w) => w.chain_type.trim().toLowerCase() === 'evm')
  return resolvePrimaryPersonCryptoWallet(evmWallets)
}

const PERSON_WALLETS_CACHE_KEY = 'portal:privy-person-wallets'

/** Bootstrap synchrone depuis le cache warmup (navigation deposit). */
export function readCachedPortalPersonCryptoWallets(): PortalPersonCryptoWallet[] {
  const cached = readPortalCache<{ wallets?: unknown }>(PERSON_WALLETS_CACHE_KEY)
  if (!cached) return []
  return parsePersonWallets(cached)
}

export async function fetchPortalPersonCryptoWallets(): Promise<PortalPersonCryptoWallet[]> {
  const res = await fetch('/api/portal/privy/person-wallets', {
    credentials: 'include',
    cache: 'no-store',
  })
  if (res.status === 401) {
    throw new Error('Session expired. Please sign in again.')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = parsePortalExchangeError(data)
    throw new Error(err.message)
  }
  writePortalCache(PERSON_WALLETS_CACHE_KEY, data, 60_000)
  return parsePersonWallets(data)
}

export async function linkPrivyForAuthenticatedSession(privyUserId: string): Promise<void> {
  const res = await fetch('/api/portal/privy/link', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ privy_user_id: privyUserId.trim() }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = parsePortalExchangeError(data)
    throw new Error(err.message)
  }
}

export async function exchangePrivyAccessTokenWithWallets(args: {
  privyAccessToken: string
  privyIdentityToken?: string | null
  wallets?: PrivyExchangeWalletPayload[]
}): Promise<void> {
  const res = await fetch('/api/portal/privy/exchange', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      privy_access_token: args.privyAccessToken,
      privy_identity_token: args.privyIdentityToken || undefined,
      signUpMode: false,
      wallets: args.wallets,
    }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = parsePortalExchangeError(data)
    throw new Error(err.message)
  }
}
