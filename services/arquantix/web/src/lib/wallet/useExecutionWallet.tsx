'use client'

import * as React from 'react'

import { findEvmPersonWallet, fetchPortalPersonCryptoWallets } from '@/lib/portal/privyWalletClient'
import {
  fetchExternalWalletMockStatus,
  fetchVerifiedExternalWallets,
  linkLocalMockExternalWalletDev,
} from '@/lib/wallet/externalWalletClient'
import type { ExecutionWallet, VerifiedExternalWallet } from '@/lib/wallet/executionWalletTypes'
import { isLocalMockVerifiedExternalWallet } from '@/lib/wallet/externalWalletMock'

const STORAGE_KEY = 'portal:execution_wallet_mode'
const MOCK_WALLET_STORAGE_KEY = 'portal:execution_wallet_mock_selected'

export type ExecutionWalletMode = 'privy_embedded' | 'external_evm'

type ExecutionWalletContextValue = {
  mode: ExecutionWalletMode
  setMode: (mode: ExecutionWalletMode) => void
  externalWallets: VerifiedExternalWallet[]
  selectedExternalWalletId: string | null
  setSelectedExternalWalletId: (id: string | null) => void
  refreshExternalWallets: () => Promise<void>
  privyEmbeddedAddress: `0x${string}` | null
  refreshPrivyEmbeddedAddress: () => Promise<void>
  resolveExecutionWallet: () => Promise<ExecutionWallet | null>
  loading: boolean
  mockWalletAvailable: boolean
  mockWalletLinked: boolean
  linkLocalMockWallet: () => Promise<VerifiedExternalWallet>
  selectLocalMockWallet: () => void
}

const ExecutionWalletContext = React.createContext<ExecutionWalletContextValue | null>(null)

function readStoredMode(): ExecutionWalletMode {
  if (typeof window === 'undefined') return 'privy_embedded'
  try {
    const value = window.localStorage.getItem(STORAGE_KEY)
    return value === 'external_evm' ? 'external_evm' : 'privy_embedded'
  } catch {
    return 'privy_embedded'
  }
}

export function ExecutionWalletProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = React.useState<ExecutionWalletMode>('privy_embedded')
  const [externalWallets, setExternalWallets] = React.useState<VerifiedExternalWallet[]>([])
  const [selectedExternalWalletId, setSelectedExternalWalletId] = React.useState<string | null>(null)
  const [privyEmbeddedAddress, setPrivyEmbeddedAddress] = React.useState<`0x${string}` | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [mockWalletAvailable, setMockWalletAvailable] = React.useState(false)
  const [mockWalletLinked, setMockWalletLinked] = React.useState(false)

  React.useEffect(() => {
    setModeState(readStoredMode())
  }, [])

  const setMode = React.useCallback((next: ExecutionWalletMode) => {
    setModeState(next)
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      /* ignore */
    }
  }, [])

  const selectLocalMockWallet = React.useCallback(() => {
    setMode('external_evm')
    try {
      window.localStorage.setItem(MOCK_WALLET_STORAGE_KEY, 'true')
    } catch {
      /* ignore */
    }
  }, [setMode])

  const refreshExternalWallets = React.useCallback(async () => {
    try {
      const wallets = await fetchVerifiedExternalWallets()
      setExternalWallets(wallets)
      setSelectedExternalWalletId((current) => {
        if (current && wallets.some((row) => row.id === current)) return current
        const mockWallet = wallets.find((row) => isLocalMockVerifiedExternalWallet(row))
        if (mockWallet) return mockWallet.id
        return wallets[0]?.id ?? null
      })
    } catch {
      setExternalWallets([])
      setSelectedExternalWalletId(null)
    }
  }, [])

  const refreshMockWalletStatus = React.useCallback(async () => {
    try {
      const status = await fetchExternalWalletMockStatus()
      setMockWalletAvailable(status.devRouteAvailable)
      setMockWalletLinked(status.linked)
    } catch {
      setMockWalletAvailable(false)
      setMockWalletLinked(false)
    }
  }, [])

  const linkLocalMockWallet = React.useCallback(async () => {
    const wallet = await linkLocalMockExternalWalletDev()
    await Promise.all([refreshExternalWallets(), refreshMockWalletStatus()])
    setSelectedExternalWalletId(wallet.id)
    selectLocalMockWallet()
    return wallet
  }, [refreshExternalWallets, refreshMockWalletStatus, selectLocalMockWallet])

  const refreshPrivyEmbeddedAddress = React.useCallback(async () => {
    try {
      const wallets = await fetchPortalPersonCryptoWallets()
      const evm = findEvmPersonWallet(wallets.filter((w) => w.provider === 'privy'))
      setPrivyEmbeddedAddress((evm?.address as `0x${string}` | undefined) ?? null)
    } catch {
      setPrivyEmbeddedAddress(null)
    }
  }, [])

  React.useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      await Promise.all([
        refreshExternalWallets(),
        refreshPrivyEmbeddedAddress(),
        refreshMockWalletStatus(),
      ])
      if (!cancelled) setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [refreshExternalWallets, refreshMockWalletStatus, refreshPrivyEmbeddedAddress])

  const resolveExecutionWallet = React.useCallback(async (): Promise<ExecutionWallet | null> => {
    if (mode === 'external_evm') {
      await refreshExternalWallets()
      const selected =
        externalWallets.find((row) => row.id === selectedExternalWalletId) ?? externalWallets[0] ?? null
      if (!selected) return null
      return {
        type: 'external_evm',
        address: selected.address,
        externalWalletId: selected.id,
        connector: selected.walletProvider,
      }
    }

    await refreshPrivyEmbeddedAddress()
    if (!privyEmbeddedAddress) return null
    return {
      type: 'privy_embedded',
      address: privyEmbeddedAddress,
    }
  }, [
    externalWallets,
    mode,
    privyEmbeddedAddress,
    refreshExternalWallets,
    refreshPrivyEmbeddedAddress,
    selectedExternalWalletId,
  ])

  const value = React.useMemo(
    () => ({
      mode,
      setMode,
      externalWallets,
      selectedExternalWalletId,
      setSelectedExternalWalletId,
      refreshExternalWallets,
      privyEmbeddedAddress,
      refreshPrivyEmbeddedAddress,
      resolveExecutionWallet,
      loading,
      mockWalletAvailable,
      mockWalletLinked,
      linkLocalMockWallet,
      selectLocalMockWallet,
    }),
    [
      externalWallets,
      linkLocalMockWallet,
      loading,
      mockWalletAvailable,
      mockWalletLinked,
      mode,
      privyEmbeddedAddress,
      refreshExternalWallets,
      refreshPrivyEmbeddedAddress,
      resolveExecutionWallet,
      selectLocalMockWallet,
      selectedExternalWalletId,
    ],
  )

  return <ExecutionWalletContext.Provider value={value}>{children}</ExecutionWalletContext.Provider>
}

export function useExecutionWallet(): ExecutionWalletContextValue {
  const ctx = React.useContext(ExecutionWalletContext)
  if (!ctx) {
    throw new Error('useExecutionWallet must be used within ExternalWalletProvider')
  }
  return ctx
}

export function useOptionalExecutionWallet(): ExecutionWalletContextValue | null {
  return React.useContext(ExecutionWalletContext)
}
