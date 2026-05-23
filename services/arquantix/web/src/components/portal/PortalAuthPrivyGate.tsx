'use client'

import * as React from 'react'
import { usePrivy } from '@privy-io/react-auth'
import { PrivyPortalProvider } from '@/components/portal/PrivyPortalProvider'

type PortalAuthPrivyContextValue = {
  privyReady: boolean
  setPrivyReady: (ready: boolean) => void
  /** App ID injecté par le layout serveur (`PRIVY_APP_ID` / ECS). */
  privyAppId: string
}

const PortalAuthPrivyContext = React.createContext<PortalAuthPrivyContextValue>({
  privyReady: false,
  setPrivyReady: () => {},
  privyAppId: '',
})

export function usePortalAuthPrivy(): PortalAuthPrivyContextValue {
  return React.useContext(PortalAuthPrivyContext)
}

function PrivyReadyReporter() {
  const { ready } = usePrivy()
  const { setPrivyReady } = usePortalAuthPrivy()

  React.useEffect(() => {
    setPrivyReady(ready)
  }, [ready, setPrivyReady])

  return null
}

type PortalAuthPrivyGateProps = {
  children: React.ReactNode
  appId: string
}

/**
 * Privy monté dès le premier render client — évite le swap children sans/s avec Provider.
 */
export function PortalAuthPrivyGate({ children, appId }: PortalAuthPrivyGateProps) {
  const [privyReady, setPrivyReady] = React.useState(false)
  const value = React.useMemo(
    () => ({ privyReady, setPrivyReady, privyAppId: appId }),
    [privyReady, appId],
  )

  return (
    <PortalAuthPrivyContext.Provider value={value}>
      <PrivyPortalProvider appId={appId}>
        <PrivyReadyReporter />
        {children}
      </PrivyPortalProvider>
    </PortalAuthPrivyContext.Provider>
  )
}
