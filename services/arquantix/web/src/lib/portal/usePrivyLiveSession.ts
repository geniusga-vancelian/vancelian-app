'use client'

import { useEffect, useRef } from 'react'
import type { ConnectedWallet, User } from '@privy-io/react-auth'
import { usePrivy, useWallets } from '@privy-io/react-auth'

export type PrivyLiveSession = {
  ready: boolean
  authenticated: boolean
  user: User | null | undefined
  wallets: ConnectedWallet[]
}

/**
 * Ref toujours à jour pour les flux async (signature LI.FI) — évite les closures React
 * périmées pendant `waitForPrivyClientReady`.
 */
export function usePrivyLiveSession(): React.MutableRefObject<PrivyLiveSession> {
  const { ready, authenticated, user } = usePrivy()
  const { wallets } = useWallets()
  const live = useRef<PrivyLiveSession>({
    ready: false,
    authenticated: false,
    user: null,
    wallets: [],
  })

  useEffect(() => {
    live.current = { ready, authenticated, user, wallets }
  }, [ready, authenticated, user, wallets])

  return live
}
