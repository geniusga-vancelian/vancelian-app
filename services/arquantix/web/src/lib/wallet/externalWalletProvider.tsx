'use client'

import '@rainbow-me/rainbowkit/styles.css'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RainbowKitProvider } from '@rainbow-me/rainbowkit'
import * as React from 'react'
import { WagmiProvider, type State } from 'wagmi'

import { externalWalletWagmiConfig } from '@/lib/wallet/externalWalletConfig'
import { ExecutionWalletProvider } from '@/lib/wallet/useExecutionWallet'

const queryClient = new QueryClient()

type Props = {
  children: React.ReactNode
  /** Hydratation SSR — persiste la session WalletConnect au retour MetaMask mobile. */
  wagmiInitialState?: State
}

export function ExternalWalletProvider({ children, wagmiInitialState }: Props) {
  return (
    <WagmiProvider
      config={externalWalletWagmiConfig}
      initialState={wagmiInitialState}
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
