'use client'

import { useCallback, useMemo, useState } from 'react'
import {
  getEmbeddedConnectedWallet,
  usePrivy,
  useSessionSigners,
  useWallets,
} from '@privy-io/react-auth'
import type { ConnectedWallet, User } from '@privy-io/react-auth'

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

/**
 * Résout l'adresse du wallet embedded EVM (Privy), robuste au portail Vancelian.
 *
 * `useWallets()` peut être vide (wallet backend sans session SDK « connectée ») :
 * on retombe alors sur `user.linkedAccounts`, comme le résolveur de signature swap.
 */
function findEmbeddedWalletAddress(
  wallets: ConnectedWallet[],
  user: User | null | undefined,
): string | null {
  const connected =
    getEmbeddedConnectedWallet(wallets) ??
    wallets.find((w) => w.walletClientType === 'privy' || w.walletClientType === 'privy-v2') ??
    wallets.find((w) => w.type === 'ethereum' && Boolean(w.address)) ??
    null
  if (connected?.address) return connected.address

  const accounts = user?.linkedAccounts
  if (accounts?.length) {
    for (const account of accounts) {
      if (account.type !== 'wallet') continue
      const w = account as {
        address?: string
        chainType?: string
        walletClientType?: string
        connectorType?: string
      }
      if (w.chainType !== 'ethereum' || !w.address) continue
      const client = (w.walletClientType || '').toLowerCase()
      const connector = (w.connectorType || '').toLowerCase()
      if (client === 'privy' || client === 'privy-v2' || connector === 'embedded') {
        return w.address
      }
    }
  }
  return null
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
  const embeddedAddress = useMemo(() => findEmbeddedWalletAddress(wallets, user), [wallets, user])

  const isDelegated = useMemo(() => {
    if (!embeddedAddress) return false
    const target = embeddedAddress.toLowerCase()
    const accounts = (user?.linkedAccounts ?? []) as unknown as Array<Record<string, unknown>>
    return accounts.some((account) => {
      if (account.type !== 'wallet') return false
      const address = typeof account.address === 'string' ? account.address.toLowerCase() : ''
      return address === target && account.delegated === true
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
