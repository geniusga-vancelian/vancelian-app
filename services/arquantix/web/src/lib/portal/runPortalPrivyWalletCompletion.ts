import {
  exchangePrivyAccessTokenWithWallets,
  fetchPortalPersonCryptoWallets,
  linkPrivyForAuthenticatedSession,
  toPrivyExchangeWalletPayload,
  type PrivyExchangeWalletPayload,
} from '@/lib/portal/privyWalletClient'

export type PortalPrivyWalletCompletionResult = 'created' | 'already_exists'

type RunPortalPrivyWalletCompletionArgs = {
  getPrivyUserId: () => string | null | undefined
  getAccessToken: () => Promise<string | null | undefined>
  getIdentityToken?: () => string | null | undefined
  createEmbeddedWallet: () => Promise<{ address: string; chainId?: string; walletType?: string }>
  findExistingEmbeddedWallet?: () => { address: string; chainId?: string; walletType?: string } | null
}

/**
 * Aligné sur Flutter `runPrivyWalletLinkExchangeAndFinish` :
 * person-wallets → link → create embedded EVM → exchange avec wallets[].
 */
export async function runPortalPrivyWalletCompletion(
  args: RunPortalPrivyWalletCompletionArgs,
): Promise<PortalPrivyWalletCompletionResult> {
  const existing = await fetchPortalPersonCryptoWallets()
  if (existing.length > 0) {
    return 'already_exists'
  }

  const privyUserId = args.getPrivyUserId()?.trim()
  if (!privyUserId) {
    throw new Error('Privy identity missing. Confirm your email and try again.')
  }

  await linkPrivyForAuthenticatedSession(privyUserId)

  let walletPayload: PrivyExchangeWalletPayload | null = null
  const embedded = args.findExistingEmbeddedWallet?.()
  if (embedded?.address) {
    walletPayload = toPrivyExchangeWalletPayload(embedded)
  } else {
    const created = await args.createEmbeddedWallet()
    walletPayload = toPrivyExchangeWalletPayload(created)
  }

  const privyToken = (await args.getAccessToken())?.trim()
  if (!privyToken) {
    throw new Error('Privy session expired. Confirm your email and try again.')
  }

  await exchangePrivyAccessTokenWithWallets({
    privyAccessToken: privyToken,
    privyIdentityToken: args.getIdentityToken?.() ?? null,
    wallets: [walletPayload],
  })

  return 'created'
}
