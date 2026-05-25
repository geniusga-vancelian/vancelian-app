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
import { buildPortalWalletScopes } from '@/lib/portal/buildPortalWalletScopes'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { fetchPortalPersonCryptoWallets } from '@/lib/portal/privyWalletClient'
import { getCurrentPortalWalletScopeId, usePortalWalletScopeId } from '@/lib/portal/portalWalletScope'
import type { PortalWalletScope, PortalWalletScopeId } from '@/lib/portal/portalWalletScopeTypes'
import { fetchPortalSolanaWalletStatus } from '@/lib/portal/solanaWalletClient'
import { fetchVerifiedExternalWallets } from '@/lib/wallet/externalWalletClient'
import { useOptionalExecutionWallet } from '@/lib/wallet/useExecutionWallet'

type PortalWalletScopeContextValue = {
  walletScope: PortalWalletScope | null
  walletScopeId: PortalWalletScopeId | null
  setWalletScopeId: (scopeId: PortalWalletScopeId | null) => void
  scopes: PortalWalletScope[]
  loading: boolean
  refreshScopes: () => Promise<void>
}

const PortalWalletScopeContext = createContext<PortalWalletScopeContextValue | null>(null)

export function PortalWalletScopeProvider({ children }: { children: ReactNode }) {
  const { chain } = usePortalChainContext()
  const execution = useOptionalExecutionWallet()
  const [walletScopeId, setWalletScopeId] = usePortalWalletScopeId()
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
      const [personResult, externalResult, solanaResult] = await Promise.allSettled([
        fetchPortalPersonCryptoWallets(),
        fetchVerifiedExternalWallets(),
        fetchPortalSolanaWalletStatus(),
      ])

      const personWallets = personResult.status === 'fulfilled' ? personResult.value : []
      const externalWallets = externalResult.status === 'fulfilled' ? externalResult.value : []
      const solanaStatus = solanaResult.status === 'fulfilled' ? solanaResult.value : null

      const built = buildPortalWalletScopes({
        chain,
        personWallets,
        externalWallets,
        solanaStatus,
      })
      setScopes(built)

      const current = getCurrentPortalWalletScopeId()
      const nextId = built[0]?.id ?? null
      if ((!current || !built.some((scope) => scope.id === current)) && nextId !== current) {
        setWalletScopeId(nextId)
      }
    } finally {
      hasLoadedRef.current = true
      setLoading(false)
      refreshInFlightRef.current = false
    }
  }, [chain, setWalletScopeId])

  useEffect(() => {
    void refreshScopes()
  }, [refreshScopes])

  const walletScope = useMemo(
    () => scopes.find((scope) => scope.id === walletScopeId) ?? scopes[0] ?? null,
    [scopes, walletScopeId],
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

  useEffect(() => {
    syncedScopeIdRef.current = null
  }, [chain])

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
