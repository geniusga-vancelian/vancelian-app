import { NextRequest, NextResponse } from 'next/server'

import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
import { isValidEvmAddress } from '@/lib/portal/morphoConstants'
import { externalWalletErrorResponse } from '@/lib/wallet/externalWalletRouteHelpers'
import { verifyAndLinkExternalWallet } from '@/lib/wallet/externalWalletVerification'

function parseVerifyBody(body: unknown) {
  if (!body || typeof body !== 'object') return null
  const row = body as Record<string, unknown>
  const walletAddress =
    typeof row.wallet_address === 'string'
      ? row.wallet_address
      : typeof row.walletAddress === 'string'
        ? row.walletAddress
        : null
  const signature = typeof row.signature === 'string' ? row.signature : null
  const nonce = typeof row.nonce === 'string' ? row.nonce : null
  const walletProvider = row.wallet_provider ?? row.walletProvider
  const chainIdRaw = row.chain_id ?? row.chainId
  const chainId =
    typeof chainIdRaw === 'number'
      ? chainIdRaw
      : typeof chainIdRaw === 'string' && chainIdRaw.trim()
        ? Number.parseInt(chainIdRaw, 10)
        : null

  if (!walletAddress || !signature || !nonce) return null
  if (!isValidEvmAddress(walletAddress)) return null
  if (!/^0x[a-fA-F0-9]+$/.test(signature.trim())) return null
  if (!nonce.trim()) return null

  return {
    walletAddress,
    signature: signature.trim() as `0x${string}`,
    nonce: nonce.trim(),
    walletProvider,
    chainId: Number.isFinite(chainId) ? chainId : null,
  }
}

/** Vérifie la signature et lie le wallet externe à la personne. */
export async function POST(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const parsed = parseVerifyBody(await request.json())
    if (!parsed) {
      return NextResponse.json({ code: 'wallet.invalid_request', message: 'Requête invalide.' }, { status: 400 })
    }

    const wallet = await verifyAndLinkExternalWallet({
      personId,
      walletAddress: parsed.walletAddress,
      signature: parsed.signature,
      nonce: parsed.nonce,
      walletProvider: parsed.walletProvider,
      chainId: parsed.chainId,
    })

    return NextResponse.json({ wallet })
  } catch (error) {
    return externalWalletErrorResponse(error)
  }
}
