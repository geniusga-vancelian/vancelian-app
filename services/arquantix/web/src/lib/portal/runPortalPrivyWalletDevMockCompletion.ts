import {
  buildPrivyDevMockWalletAddress,
  buildPrivyDevMockWalletId,
  buildPrivyDevStubAccessToken,
  buildPrivyDevStubExternalSubject,
} from '@/lib/portal/privyOtpDevMock'
import { isPortalPrivyOtpDevMockEnabled } from '@/lib/portal/privyOtpDevMockConfig'
import type { PortalPrivyWalletCompletionResult } from '@/lib/portal/runPortalPrivyWalletCompletion'
import {
  exchangePrivyAccessTokenWithWallets,
  fetchPortalPersonCryptoWallets,
  linkPrivyForAuthenticatedSession,
  toPrivyExchangeWalletPayload,
} from '@/lib/portal/privyWalletClient'

/**
 * Création / lien wallet sans SDK Privy (stub + adresse mock par e-mail).
 * Requiert `PRIVY_EXCHANGE_VERIFICATION_MODE=stub` côté API.
 */
export async function runPortalPrivyWalletDevMockCompletion(
  email: string,
): Promise<PortalPrivyWalletCompletionResult> {
  if (!isPortalPrivyOtpDevMockEnabled()) {
    throw new Error('Privy OTP dev mock is not enabled.')
  }

  const trimmed = email.trim()
  if (!trimmed.includes('@')) {
    throw new Error('A valid email is required for dev wallet mock.')
  }

  const existing = await fetchPortalPersonCryptoWallets()
  if (existing.length > 0) {
    return 'already_exists'
  }

  const stubSubject = buildPrivyDevStubExternalSubject(trimmed)
  await linkPrivyForAuthenticatedSession(stubSubject)

  await exchangePrivyAccessTokenWithWallets({
    privyAccessToken: buildPrivyDevStubAccessToken(trimmed),
    email: trimmed,
    wallets: [
      toPrivyExchangeWalletPayload({
        address: buildPrivyDevMockWalletAddress(trimmed),
        walletType: 'embedded',
        privyWalletId: buildPrivyDevMockWalletId(trimmed),
      }),
    ],
  })

  return 'created'
}
