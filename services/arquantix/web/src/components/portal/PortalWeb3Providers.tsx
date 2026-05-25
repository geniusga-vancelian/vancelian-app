'use client'

import { ExternalWalletProvider } from '@/lib/wallet/externalWalletProvider'

type Props = {
  children: React.ReactNode
}

/** Wagmi + RainbowKit + sélection wallet d’exécution (portail client). */
export function PortalWeb3Providers({ children }: Props) {
  return <ExternalWalletProvider>{children}</ExternalWalletProvider>
}
