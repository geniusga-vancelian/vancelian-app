'use client'

import { createContext, useContext, type ReactNode } from 'react'
import { type PortalChain } from '@/config/portalChains'
import { usePortalChain } from '@/lib/portal/portalChain'

type PortalChainContextValue = {
  chain: PortalChain
  setChain: (chain: PortalChain) => void
}

const PortalChainContext = createContext<PortalChainContextValue | null>(null)

export function PortalChainProvider({ children }: { children: ReactNode }) {
  const [chain, setChain] = usePortalChain()
  return (
    <PortalChainContext.Provider value={{ chain, setChain }}>
      {children}
    </PortalChainContext.Provider>
  )
}

export function usePortalChainContext(): PortalChainContextValue {
  const ctx = useContext(PortalChainContext)
  if (!ctx) {
    throw new Error('usePortalChainContext must be used within PortalChainProvider')
  }
  return ctx
}
