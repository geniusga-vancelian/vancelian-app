import { PortalAuthPrivyGate } from '@/components/portal/PortalAuthPrivyGate'
import { getPrivyAppIdServer } from '@/lib/portal/privyConfig'

/** Privy requis pour swap (signature LI.FI) et création wallet embedded. */
export default function PortalWalletLayout({ children }: { children: React.ReactNode }) {
  const appId = getPrivyAppIdServer()
  return <PortalAuthPrivyGate appId={appId}>{children}</PortalAuthPrivyGate>
}
