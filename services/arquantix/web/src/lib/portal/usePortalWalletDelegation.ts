'use client'

import { useCallback, useMemo, useState } from 'react'
import { usePrivy, useSessionSigners, useWallets } from '@privy-io/react-auth'

import { getPrivyAuthorizationQuorumId } from '@/lib/portal/privyConfig'

export type PortalWalletDelegationState = {
  /** Quorum d'autorisation configuré (sinon délégation indisponible). */
  isConfigured: boolean
  /** Wallet embedded déjà délégué au signer serveur de l'app. */
  isDelegated: boolean
  /** Délégation possible (configurée, wallet présent, pas déjà délégué). */
  canDelegate: boolean
  /** Révocation possible (configurée, wallet présent, déjà délégué). */
  canRevoke: boolean
  /** Opération de délégation/révocation en cours. */
  isPending: boolean
  error: string | null
  /** Déclenche le consentement utilisateur (one-time) pour l'exécution automatique. */
  delegate: () => Promise<boolean>
  /** Révoque le signer serveur de l'app (désactive l'exécution automatique). */
  revoke: () => Promise<boolean>
}

function findEmbeddedWalletAddress(wallets: ReturnType<typeof useWallets>['wallets']): string | null {
  const embedded = wallets.find((wallet) => wallet.walletClientType === 'privy')
  return embedded?.address ? embedded.address.toLowerCase() : null
}

/**
 * Délégation one-time du wallet embedded de l'utilisateur au key-quorum de l'app
 * (Privy Session Signers), prérequis à l'exécution serveur/worker sans navigateur.
 */
export function usePortalWalletDelegation(): PortalWalletDelegationState {
  const quorumId = getPrivyAuthorizationQuorumId()
  const { user } = usePrivy()
  const { wallets } = useWallets()
  const { addSessionSigners, removeSessionSigners } = useSessionSigners()
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isConfigured = Boolean(quorumId)
  const embeddedAddress = useMemo(() => findEmbeddedWalletAddress(wallets), [wallets])

  const isDelegated = useMemo(() => {
    if (!embeddedAddress) return false
    const accounts = (user?.linkedAccounts ?? []) as unknown as Array<Record<string, unknown>>
    return accounts.some((account) => {
      if (account.type !== 'wallet') return false
      const address = typeof account.address === 'string' ? account.address.toLowerCase() : ''
      return address === embeddedAddress && account.delegated === true
    })
  }, [user, embeddedAddress])

  const canDelegate = isConfigured && Boolean(embeddedAddress) && !isDelegated
  const canRevoke = isConfigured && Boolean(embeddedAddress) && isDelegated

  const delegate = useCallback(async (): Promise<boolean> => {
    if (!isConfigured) {
      setError("Exécution automatique indisponible (configuration manquante).")
      return false
    }
    if (!embeddedAddress) {
      setError('Wallet Vancelian requis — créez votre wallet crypto depuis Mon wallet.')
      return false
    }
    setIsPending(true)
    setError(null)
    try {
      await addSessionSigners({
        address: embeddedAddress,
        signers: [{ signerId: quorumId, policyIds: [] }],
      })
      return true
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Échec de l'activation de l'exécution automatique.",
      )
      return false
    } finally {
      setIsPending(false)
    }
  }, [isConfigured, embeddedAddress, addSessionSigners, quorumId])

  const revoke = useCallback(async (): Promise<boolean> => {
    if (!embeddedAddress) {
      setError('Wallet Vancelian requis — créez votre wallet crypto depuis Mon wallet.')
      return false
    }
    setIsPending(true)
    setError(null)
    try {
      await removeSessionSigners({ address: embeddedAddress })
      return true
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Échec de la révocation de l'exécution automatique.",
      )
      return false
    } finally {
      setIsPending(false)
    }
  }, [embeddedAddress, removeSessionSigners])

  return { isConfigured, isDelegated, canDelegate, canRevoke, isPending, error, delegate, revoke }
}
