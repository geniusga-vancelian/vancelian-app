'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  buildEmbeddedVancelianWalletScope,
  buildSwitchablePortalWalletScopes,
} from '@/lib/portal/buildPortalWalletScopes'
import { fetchPortalPersonCryptoWallets } from '@/lib/portal/privyWalletClient'
import { getCurrentPortalWalletScopeId, usePortalWalletScopeId } from '@/lib/portal/portalWalletScope'
import type { PortalWalletScope, PortalWalletScopeId } from '@/lib/portal/portalWalletScopeTypes'
import { fetchVerifiedExternalWallets } from '@/lib/wallet/externalWalletClient'
import { useOptionalExecutionWallet } from '@/lib/wallet/useExecutionWallet'

type PortalWalletScopeContextValue = {
  walletScope: PortalWalletScope | null
  walletScopeId: PortalWalletScopeId | null
  setWalletScopeId: (scopeId: PortalWalletScopeId | null) => void
  /** Wallets affichés dans le sélecteur navbar (externes uniquement). */
  scopes: PortalWalletScope[]
  loading: boolean
  refreshScopes: () => Promise<void>
}

const PortalWalletScopeContext = createContext<PortalWalletScopeContextValue | null>(null)

function resolveActiveWalletScope(
  scopeId: PortalWalletScopeId | null,
  embedded: PortalWalletScope | null,
  switchable: PortalWalletScope[],
): PortalWalletScope | null {
  if (scopeId?.startsWith('external:')) {
    return switchable.find((scope) => scope.id === scopeId) ?? embedded
  }
  return embedded
}

export function PortalWalletScopeProvider({ children }: { children: ReactNode }) {
  const execution = useOptionalExecutionWallet()
  const [walletScopeId, setWalletScopeId] = usePortalWalletScopeId()
  const [embeddedScope, setEmbeddedScope] = useState<PortalWalletScope | null>(null)
  const [scopes, setScopes] = useState<PortalWalletScope[]>([])
  const [loading, setLoading] = useState(true)
  const hasLoadedRef = useRef(false)
  const refreshInFlightRef = useRef(false)
  const syncedScopeIdRef = useRef<string | null>(null)

  const refreshScopes = useCallback(async () => {
    if (refreshInFlightRef.current) return
    refreshInFlightRef.current = true

    if (!hasLoadedRef.current) {
      setLoading(true)
    }

    try {
      const [personResult, externalResult] = await Promise.allSettled([
        fetchPortalPersonCryptoWallets(),
        fetchVerifiedExternalWallets(),
      ])

      const personWallets = personResult.status === 'fulfilled' ? personResult.value : []
      const externalWallets = externalResult.status === 'fulfilled' ? externalResult.value : []

      const embedded = buildEmbeddedVancelianWalletScope(personWallets)
      const switchable = buildSwitchablePortalWalletScopes({ externalWallets })
      setEmbeddedScope(embedded)
      setScopes(switchable)

      const current = getCurrentPortalWalletScopeId()
      if (current?.startsWith('external:') && switchable.some((scope) => scope.id === current)) {
        setWalletScopeId(current)
        return
      }

      if (embedded) {
        setWalletScopeId(embedded.id)
      } else if (switchable[0]) {
        setWalletScopeId(switchable[0].id)
      }
    } finally {
      hasLoadedRef.current = true
      setLoading(false)
      refreshInFlightRef.current = false
    }
  }, [setWalletScopeId])

  useEffect(() => {
    void refreshScopes()
  }, [refreshScopes])

  const walletScope = useMemo(
    () => resolveActiveWalletScope(walletScopeId, embeddedScope, scopes),
    [embeddedScope, scopes, walletScopeId],
  )

  const setExecutionMode = execution?.setMode
  const setSelectedExternalWalletId = execution?.setSelectedExternalWalletId

  useEffect(() => {
    if (!setExecutionMode || !walletScope) return
    if (syncedScopeIdRef.current === walletScope.id) return
    syncedScopeIdRef.current = walletScope.id

    if (walletScope.kind === 'external_evm' && walletScope.externalWalletId) {
      setExecutionMode('external_evm')
      setSelectedExternalWalletId?.(walletScope.externalWalletId)
      return
    }
    setExecutionMode('privy_embedded')
  }, [setExecutionMode, setSelectedExternalWalletId, walletScope])

  const value = useMemo(
    () => ({
      walletScope,
      walletScopeId: walletScope?.id ?? walletScopeId,
      setWalletScopeId,
      scopes,
      loading,
      refreshScopes,
    }),
    [loading, refreshScopes, scopes, setWalletScopeId, walletScope, walletScopeId],
  )

  return (
    <PortalWalletScopeContext.Provider value={value}>{children}</PortalWalletScopeContext.Provider>
  )
}

export function usePortalWalletScopeContext(): PortalWalletScopeContextValue {
  const ctx = useContext(PortalWalletScopeContext)
  if (!ctx) {
    throw new Error('usePortalWalletScopeContext must be used within PortalWalletScopeProvider')
  }
  return ctx
}
