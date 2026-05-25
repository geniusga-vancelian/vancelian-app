'use client'

import '@rainbow-me/rainbowkit/styles.css'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RainbowKitProvider } from '@rainbow-me/rainbowkit'
import * as React from 'react'
import { WagmiProvider, cookieToInitialState, type State } from 'wagmi'

import { getExternalWalletWagmiConfig } from '@/lib/wallet/externalWalletConfig'
import { ExecutionWalletProvider } from '@/lib/wallet/useExecutionWallet'

const queryClient = new QueryClient()

type Props = {
  children: React.ReactNode
  /** Cookies HTTP bruts — hydratation WalletConnect côté client uniquement (RainbowKit ne bundle pas en SSR). */
  wagmiCookieHeader?: string
  /** Hydratation SSR explicite (tests / overrides). */
  wagmiInitialState?: State
}

export function ExternalWalletProvider({ children, wagmiCookieHeader, wagmiInitialState }: Props) {
  const resolvedInitialState = React.useMemo(() => {
    if (wagmiInitialState) return wagmiInitialState
    if (!wagmiCookieHeader) return undefined
    return cookieToInitialState(getExternalWalletWagmiConfig(), wagmiCookieHeader)
  }, [wagmiCookieHeader, wagmiInitialState])

  return (
    <WagmiProvider
      config={getExternalWalletWagmiConfig()}
      initialState={resolvedInitialState}
      reconnectOnMount
    >
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider locale="fr-FR">
          <ExecutionWalletProvider>{children}</ExecutionWalletProvider>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  )
}
