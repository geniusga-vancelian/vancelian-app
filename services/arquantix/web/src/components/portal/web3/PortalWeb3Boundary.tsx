'use client'

import type { ReactNode } from 'react'

import { PortalAuthPrivyGate } from '@/components/portal/PortalAuthPrivyGate'
import { PortalWeb3Providers } from '@/components/portal/PortalWeb3Providers'

type Props = {
  children: ReactNode
  wagmiCookieHeader?: string | null
  appId?: string | null
}

/** Boundary Web3 explicite — Privy + Wagmi + RainbowKit (routes wallet / exécution uniquement). */
export function PortalWeb3Boundary({ children, wagmiCookieHeader, appId = '' }: Props) {
  return (
    <PortalWeb3Providers wagmiCookieHeader={wagmiCookieHeader ?? undefined}>
      <PortalAuthPrivyGate appId={appId ?? ''}>{children}</PortalAuthPrivyGate>
    </PortalWeb3Providers>
  )
}
