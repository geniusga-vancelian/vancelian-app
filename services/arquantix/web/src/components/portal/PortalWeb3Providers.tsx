'use client'

import { ExternalWalletProvider } from '@/lib/wallet/externalWalletProvider'

type Props = {
  children: React.ReactNode
  wagmiCookieHeader?: string
}

/** Wagmi + RainbowKit + sélection wallet d’exécution (portail client). */
export function PortalWeb3Providers({ children, wagmiCookieHeader }: Props) {
  return (
    <ExternalWalletProvider wagmiCookieHeader={wagmiCookieHeader}>{children}</ExternalWalletProvider>
  )
}
