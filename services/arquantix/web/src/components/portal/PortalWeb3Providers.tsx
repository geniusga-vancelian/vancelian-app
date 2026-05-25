'use client'

import type { State } from 'wagmi'

import { ExternalWalletProvider } from '@/lib/wallet/externalWalletProvider'

type Props = {
  children: React.ReactNode
  wagmiCookieHeader?: string
  wagmiInitialState?: State
}

/** Wagmi + RainbowKit + sélection wallet d’exécution (portail client). */
export function PortalWeb3Providers({ children, wagmiCookieHeader, wagmiInitialState }: Props) {
  return (
    <ExternalWalletProvider wagmiCookieHeader={wagmiCookieHeader} wagmiInitialState={wagmiInitialState}>
      {children}
    </ExternalWalletProvider>
  )
}
