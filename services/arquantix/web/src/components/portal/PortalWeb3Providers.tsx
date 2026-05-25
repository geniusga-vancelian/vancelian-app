'use client'

import type { State } from 'wagmi'

import { ExternalWalletProvider } from '@/lib/wallet/externalWalletProvider'

type Props = {
  children: React.ReactNode
  wagmiInitialState?: State
}

/** Wagmi + RainbowKit + sélection wallet d’exécution (portail client). */
export function PortalWeb3Providers({ children, wagmiInitialState }: Props) {
  return (
    <ExternalWalletProvider wagmiInitialState={wagmiInitialState}>{children}</ExternalWalletProvider>
  )
}
