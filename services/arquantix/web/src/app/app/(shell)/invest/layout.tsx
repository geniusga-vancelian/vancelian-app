import { PortalAuthPrivyGate } from '@/components/portal/PortalAuthPrivyGate'
import { getPrivyAppIdServer } from '@/lib/portal/privyConfig'

/** Privy requis pour Earn Morpho (dépôt / retrait vault). */
export default function PortalInvestLayout({ children }: { children: React.ReactNode }) {
  const appId = getPrivyAppIdServer()
  return <PortalAuthPrivyGate appId={appId}>{children}</PortalAuthPrivyGate>
}
