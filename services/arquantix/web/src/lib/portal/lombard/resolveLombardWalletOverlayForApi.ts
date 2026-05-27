import type { NextRequest } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { DEFAULT_PORTAL_CHAIN, isValidPortalChain, type PortalChain } from '@/config/portalChains'
import { isLombardV1Enabled } from '@/lib/portal/lombard/lombardConfig'
import { isLombardMockEnabled } from '@/lib/portal/lombard/lombardMockConfig'
import { fetchLombardActivePositionsForWallet } from '@/lib/portal/lombard/lombardPositionService'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import { applyLombardWalletBalanceOverlay } from '@/lib/portal/lombard/lombardWalletBalanceOverlay'
import { ensureLombardMockPrivyLedgerCredits } from '@/lib/portal/lombard/lombardMockPrivyLedgerCredit'
import { isValidEvmAddress } from '@/lib/portal/morphoConstants'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
import {
  findEvmPersonWallet,
  type PortalPersonCryptoWallet,
} from '@/lib/portal/privyWalletClient'
import {
  readPortalAccessToken,
  readPortalDeviceIdFromRequest,
} from '@/lib/portal/portalSession'
import type { PortalCryptoPositionsSummary } from '@/lib/portal/cryptoWalletTypes'

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

/** Résout l'adresse EVM pour l'overlay Lombard (query navbar ou wallet Privy primaire). */
export async function resolveLombardOverlayWalletAddress(args: {
  request?: NextRequest
  walletFromQuery: string | null
}): Promise<string | null> {
  const fromQuery = args.walletFromQuery?.trim() ?? ''
  if (fromQuery && isValidEvmAddress(fromQuery)) return fromQuery

  const token = await readPortalAccessToken()
  if (!token) return null

  const deviceId = args.request ? readPortalDeviceIdFromRequest(args.request) : ''
  const res = await fetch(buildBackendUrl('/auth/privy/person-wallets'), {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
      'X-Device-ID': deviceId,
    },
    cache: 'no-store',
    signal: AbortSignal.timeout(15000),
  })
  if (!res.ok) return null

  const data = await res.json().catch(() => null)
  const wallet = findEvmPersonWallet(parsePersonWallets(data))
  return wallet?.address?.trim() || null
}

export async function maybeApplyLombardWalletOverlay(args: {
  personId: string
  portalChain: PortalChain
  walletAddress: string | null
  summary: PortalCryptoPositionsSummary
}): Promise<PortalCryptoPositionsSummary> {
  if (!isLombardV1Enabled()) return args.summary
  if (args.portalChain !== 'base') return args.summary

  const wallet = args.walletAddress?.trim() ?? ''
  if (!wallet || !isValidEvmAddress(wallet)) return args.summary

  await assertPortalWalletAddressOwnership({ personId: args.personId, walletAddress: wallet })

  let lombardPositions: LombardActivePosition[] = []
  try {
    lombardPositions = await fetchLombardActivePositionsForWallet(wallet)
  } catch {
    return args.summary
  }

  if (lombardPositions.length === 0) return args.summary

  if (isLombardMockEnabled()) {
    try {
      await ensureLombardMockPrivyLedgerCredits({
        personId: args.personId,
        walletAddress: wallet,
      })
    } catch (error) {
      console.warn('[lombard] mock Privy ledger backfill skipped:', error)
    }
  }

  return applyLombardWalletBalanceOverlay({
    summary: args.summary,
    lombardPositions,
    simulatePrivyBalances: isLombardMockEnabled(),
  })
}

export function resolvePortalChainFromSearchParams(raw: string | null): PortalChain {
  const value = raw?.trim().toLowerCase() ?? ''
  return isValidPortalChain(value) ? value : DEFAULT_PORTAL_CHAIN
}
