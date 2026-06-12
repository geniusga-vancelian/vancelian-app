import { NextRequest, NextResponse } from 'next/server'
import { loadCryptoWalletDetailCore } from '@/lib/portal/cryptoWalletDetailUpstream'
import {
  resolveLombardOverlayWalletAddress,
  resolvePortalChainFromSearchParams,
} from '@/lib/portal/lombard/resolveLombardWalletOverlayForApi'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
import type { PortalWalletScope } from '@/lib/portal/portalWalletScopeTypes'
import type { PortalChain } from '@/config/portalChains'

function resolveWalletScope(request: NextRequest, chain: PortalChain): PortalWalletScope | null {
  const walletAddress = request.nextUrl.searchParams.get('wallet_address')?.trim()
  if (!walletAddress) return null
  return {
    id: `scope:${walletAddress}`,
    kind: 'privy_embedded',
    label: 'Privy',
    shortLabel: 'Privy',
    address: walletAddress,
    chainType: chain === 'solana' ? 'solana' : 'evm',
  }
}

/** Détail position crypto — section core (header valeur + cotation marché). */
export async function GET(request: NextRequest, { params }: { params: { asset: string } }) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const personId = await requirePortalPersonId()
  if (personId instanceof NextResponse) return personId

  const asset = (params.asset ?? '').trim().toUpperCase()
  if (!asset) {
    return NextResponse.json({ error: 'invalid_asset' }, { status: 400 })
  }

  try {
    const portalChain = resolvePortalChainFromSearchParams(
      request.nextUrl.searchParams.get('portal_chain'),
    )
    const walletScope = resolveWalletScope(request, portalChain)
    const walletAddress = await resolveLombardOverlayWalletAddress({
      request,
      walletFromQuery: walletScope?.address ?? null,
    })

    const core = await loadCryptoWalletDetailCore({
      asset,
      personId,
      portalChain,
      walletScope,
      walletAddress,
    })

    if (!core) {
      return NextResponse.json({ error: 'not_found' }, { status: 404 })
    }
    return NextResponse.json(core)
  } catch (error) {
    console.error('[api/portal/crypto-wallet/[asset]/core GET]', error)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}
