'use client'

import dynamic from 'next/dynamic'
import type { ReactNode } from 'react'

import { getPrivyAppId } from '@/lib/portal/privyConfig'

const PortalWeb3Boundary = dynamic(
  () => import('./PortalWeb3Boundary').then((m) => m.PortalWeb3Boundary),
  {
    ssr: false,
    loading: () => (
      <div
        className="flex min-h-[48px] items-center justify-center rounded-v-card border border-v-fg-10 bg-v-fg-02 px-4 py-3"
        aria-busy="true"
        aria-live="polite"
      >
        <span className="font-ui text-[13px] text-v-fg-muted">Chargement wallet…</span>
      </div>
    ),
  },
)

type Props = {
  children: ReactNode
  wagmiCookieHeader?: string | null
  appId?: string | null
}

/** Lazy boundary Web3 — modales / sections profil sans montage global shell. */
export function PortalWeb3BoundaryLazy({ children, wagmiCookieHeader, appId }: Props) {
  return (
    <PortalWeb3Boundary
      appId={appId ?? getPrivyAppId()}
      wagmiCookieHeader={wagmiCookieHeader}
    >
      {children}
    </PortalWeb3Boundary>
  )
}
