import { NextResponse } from 'next/server'

import { ExternalWalletError } from '@/lib/wallet/externalWalletVerification'

export function externalWalletErrorResponse(error: unknown): NextResponse {
  if (error instanceof ExternalWalletError) {
    return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
  }
  console.error('[portal/wallets/external]', error)
  return NextResponse.json(
    { code: 'wallet.internal_error', message: 'Erreur interne.' },
    { status: 500 },
  )
}
