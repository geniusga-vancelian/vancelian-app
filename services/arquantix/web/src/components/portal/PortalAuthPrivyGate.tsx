'use client'

import * as React from 'react'
import { usePrivy } from '@privy-io/react-auth'
import type { PrivyPortalProvider } from '@/components/portal/PrivyPortalProvider'
import { preloadPrivyPortalProvider } from '@/lib/portal/preloadPrivyPortalProvider'

type PortalAuthPrivyContextValue = {
  privyReady: boolean
  setPrivyReady: (ready: boolean) => void
}

const PortalAuthPrivyContext = React.createContext<PortalAuthPrivyContextValue>({
  privyReady: false,
  setPrivyReady: () => {},
})

export function usePortalAuthPrivy(): PortalAuthPrivyContextValue {
  return React.useContext(PortalAuthPrivyContext)
}

function PrivyReadyReporter() {
  const { ready } = usePrivy()
  const { setPrivyReady } = usePortalAuthPrivy()

  React.useEffect(() => {
    setPrivyReady(ready)
    return () => setPrivyReady(false)
  }, [ready, setPrivyReady])

  return null
}

type PortalAuthPrivyGateProps = {
  children: React.ReactNode
  appId: string
}

/**
 * Boot Privy en arrière-plan — le shell login s’affiche sans attendre le SDK.
 */
export function PortalAuthPrivyGate({ children, appId }: PortalAuthPrivyGateProps) {
  const [PrivyProvider, setPrivyProvider] = React.useState<
    typeof PrivyPortalProvider | null
  >(null)
  const [privyReady, setPrivyReady] = React.useState(false)
  const value = React.useMemo(() => ({ privyReady, setPrivyReady }), [privyReady])

  React.useEffect(() => {
    let cancelled = false
    void preloadPrivyPortalProvider()?.then((mod) => {
      if (!cancelled) setPrivyProvider(() => mod.PrivyPortalProvider)
    })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <PortalAuthPrivyContext.Provider value={value}>
      {PrivyProvider ? (
        <PrivyProvider appId={appId}>
          <PrivyReadyReporter />
          {children}
        </PrivyProvider>
      ) : (
        children
      )}
    </PortalAuthPrivyContext.Provider>
  )
}
