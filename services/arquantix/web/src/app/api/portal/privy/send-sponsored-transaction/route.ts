import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { PortalForbiddenError } from '@/lib/portal/portalWalletOwnership'
import { requirePortalPersonId } from '@/lib/portal/portalWalletRouteHelpers'
import { PrivyServerApiError, privyServerApiConfigured, sendPrivySponsoredEthereumTransaction } from '@/lib/portal/privyServerApi'
import { resolvePrivyWalletIdForPerson } from '@/lib/portal/resolvePrivyWalletIdForPerson'

const requestSchema = z.object({
  chain_id: z.coerce.number().int().positive(),
  to: z.string().regex(/^0x[0-9a-fA-F]{40}$/),
  data: z.string().regex(/^0x[0-9a-fA-F]*$/),
  value: z.union([z.string(), z.number()]).optional(),
  gas_limit: z.union([z.string(), z.number()]).optional(),
  wallet_address: z.string().regex(/^0x[0-9a-fA-F]{40}$/),
  privy_wallet_id: z.string().trim().min(1).optional(),
  authorization_signature: z.string().trim().min(1),
})

function mapRouteError(error: unknown): NextResponse {
  if (error instanceof PortalForbiddenError) {
    return NextResponse.json({ code: 'portal.forbidden_wallet', message: error.message }, { status: 403 })
  }
  if (error instanceof PrivyServerApiError) {
    console.warn('[api/portal/privy/send-sponsored-transaction]', {
      code: error.code,
      status: error.httpStatus ?? 502,
      message: error.message,
    })
    return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus ?? 502 })
  }
  if (error instanceof z.ZodError) {
    return NextResponse.json({ code: 'privy.invalid_request', message: 'Requête transaction invalide.' }, { status: 400 })
  }
  console.error('[api/portal/privy/send-sponsored-transaction POST]', error)
  return NextResponse.json(
    { code: 'privy.send_failed', message: error instanceof Error ? error.message : 'Envoi transaction impossible.' },
    { status: 500 },
  )
}

/** Relais serveur Privy — gas sponsorship via PRIVY_APP_SECRET (jamais côté client). */
export async function POST(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    if (!privyServerApiConfigured()) {
      return NextResponse.json(
        {
          code: 'privy.server_not_configured',
          message: 'Gas sponsorship Privy indisponible (PRIVY_APP_SECRET manquant côté serveur).',
        },
        { status: 503 },
      )
    }

    const body = requestSchema.parse(await request.json())
    const privyWalletId = await resolvePrivyWalletIdForPerson({
      personId,
      walletAddress: body.wallet_address,
      privyWalletIdHint: body.privy_wallet_id ?? null,
    })

    const result = await sendPrivySponsoredEthereumTransaction({
      privyWalletId,
      authorizationSignature: body.authorization_signature,
      chainId: body.chain_id,
      to: body.to,
      data: body.data,
      value: body.value,
      gasLimit: body.gas_limit,
    })

    return NextResponse.json({
      hash: result.hash,
      transaction_id: result.transactionId ?? null,
    })
  } catch (error) {
    return mapRouteError(error)
  }
}
