'use client'

import { useCallback, useMemo } from 'react'
import {
  useAuthorizationSignature,
  usePrivy,
  useWallets,
  getEmbeddedConnectedWallet,
} from '@privy-io/react-auth'

import { PRIVY_EARN_API_BASE } from '@/lib/portal/privyEarnConfig'
import {
  fetchPortalEarnPosition,
  submitPortalEarnDeposit,
  submitPortalEarnWithdraw,
} from '@/lib/portal/privyEarnClient'
import { getPrivyAppId } from '@/lib/portal/privyConfig'

function findEmbeddedPrivyWalletId(user: ReturnType<typeof usePrivy>['user']): string | null {
  const accounts = user?.linkedAccounts ?? []
  for (const account of accounts) {
    if (account.type !== 'wallet') continue
    const wallet = account as {
      id?: string | null
      chainType?: string
      walletClientType?: string
      connectorType?: string
    }
    if (wallet.chainType !== 'ethereum') continue
    const client = (wallet.walletClientType || '').toLowerCase()
    const connector = (wallet.connectorType || '').toLowerCase()
    if (client === 'privy' || client === 'privy-v2' || connector === 'embedded') {
      return wallet.id?.trim() || null
    }
  }
  return null
}

export function usePortalPrivyEarnWallet() {
  const { ready, authenticated, user } = usePrivy()
  const { wallets } = useWallets()
  const { generateAuthorizationSignature } = useAuthorizationSignature()

  const embeddedWallet = useMemo(
    () => getEmbeddedConnectedWallet(wallets) ?? wallets.find((w) => w.walletClientType === 'privy') ?? null,
    [wallets],
  )

  const privyWalletId = useMemo(() => {
    const fromLinked = findEmbeddedPrivyWalletId(user)
    if (fromLinked) return fromLinked
    const connected = embeddedWallet as { id?: string | null } | null
    return connected?.id?.trim() || null
  }, [embeddedWallet, user])

  const walletAddress = embeddedWallet?.address ?? null

  const signEarnRequest = useCallback(
    async (
      operation: 'deposit' | 'withdraw',
      amount: string,
      vaultId: string,
      idempotencyKey: string,
    ) => {
      if (!privyWalletId) {
        throw new Error('Wallet Privy embedded introuvable. Créez votre wallet crypto puis réessayez.')
      }
      const appId = getPrivyAppId()
      if (!appId) throw new Error('Privy non configuré.')

      const path = `/v1/wallets/${privyWalletId}/earn/ethereum/${operation}`
      const url = `${PRIVY_EARN_API_BASE}${path}`
      const body = { vault_id: vaultId, amount }

      const { signature } = await generateAuthorizationSignature({
        version: 1,
        method: 'POST',
        url,
        body,
        headers: {
          'privy-app-id': appId,
          'privy-idempotency-key': idempotencyKey,
        },
      })

      return { signature, idempotencyKey }
    },
    [generateAuthorizationSignature, privyWalletId],
  )

  const loadPosition = useCallback(
    async (vaultId: string) => {
      if (!privyWalletId) return null
      return fetchPortalEarnPosition({ vaultId, privyWalletId })
    },
    [privyWalletId],
  )

  const deposit = useCallback(
    async (vaultId: string, amount: string, idempotencyKey: string) => {
      if (!ready || !authenticated) {
        throw new Error('Connectez-vous et activez votre wallet Privy pour déposer.')
      }
      if (!privyWalletId) {
        throw new Error('Wallet Privy embedded requis — créez-le depuis Mon wallet crypto.')
      }
      const auth = await signEarnRequest('deposit', amount, vaultId, idempotencyKey)
      return submitPortalEarnDeposit({
        vaultId,
        privyWalletId,
        amount,
        authorizationSignature: auth.signature,
        idempotencyKey: auth.idempotencyKey,
      })
    },
    [authenticated, privyWalletId, ready, signEarnRequest],
  )

  const withdraw = useCallback(
    async (vaultId: string, amount: string, idempotencyKey: string) => {
      if (!ready || !authenticated) {
        throw new Error('Connectez-vous et activez votre wallet Privy pour retirer.')
      }
      if (!privyWalletId) {
        throw new Error('Wallet Privy embedded requis — créez-le depuis Mon wallet crypto.')
      }
      const auth = await signEarnRequest('withdraw', amount, vaultId, idempotencyKey)
      return submitPortalEarnWithdraw({
        vaultId,
        privyWalletId,
        amount,
        authorizationSignature: auth.signature,
        idempotencyKey: auth.idempotencyKey,
      })
    },
    [authenticated, privyWalletId, ready, signEarnRequest],
  )

  return {
    ready,
    authenticated,
    privyWalletId,
    walletAddress,
    loadPosition,
    deposit,
    withdraw,
  }
}
