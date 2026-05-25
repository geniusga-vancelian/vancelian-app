'use client'

import '@rainbow-me/rainbowkit/styles.css'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RainbowKitProvider } from '@rainbow-me/rainbowkit'
import * as React from 'react'
import { WagmiProvider } from 'wagmi'

import { createExternalWalletWagmiConfig } from '@/lib/wallet/externalWalletConfig'
import { ExecutionWalletProvider } from '@/lib/wallet/useExecutionWallet'

const queryClient = new QueryClient()

type Props = {
  children: React.ReactNode
}

export function ExternalWalletProvider({ children }: Props) {
  const [config] = React.useState(() => createExternalWalletWagmiConfig())

  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider locale="fr-FR">
          <ExecutionWalletProvider>{children}</ExecutionWalletProvider>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  )
}
