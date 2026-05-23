import type { Metadata } from 'next'
import { PortalAuthPrivyGate } from '@/components/portal/PortalAuthPrivyGate'
import { getPrivyAppIdServer } from '@/lib/portal/privyConfig'
import '@/styles/portal-auth.css'

export const metadata: Metadata = {
  title: 'Vancelian — Create wallet',
  robots: { index: false, follow: false },
}

export default function PortalWalletCreateLayout({ children }: { children: React.ReactNode }) {
  const appId = getPrivyAppIdServer()
  return <PortalAuthPrivyGate appId={appId}>{children}</PortalAuthPrivyGate>
}
