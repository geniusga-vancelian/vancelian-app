import type { Metadata } from 'next'
import { PrivyPortalProvider } from '@/components/portal/PrivyPortalProvider'
import { getPrivyAppIdServer } from '@/lib/portal/privyConfig'

export const metadata: Metadata = {
  title: 'Vancelian — Espace client',
  robots: { index: false, follow: false },
}

export default function PortalAppLayout({ children }: { children: React.ReactNode }) {
  const appId = getPrivyAppIdServer()
  return <PrivyPortalProvider appId={appId}>{children}</PrivyPortalProvider>
}
