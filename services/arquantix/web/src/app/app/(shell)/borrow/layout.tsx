import { PortalAuthPrivyGate } from '@/components/portal/PortalAuthPrivyGate'
import { getPrivyAppIdServer } from '@/lib/portal/privyConfig'

/** Privy requis pour signer approve + open loan Lombard (cbBTC/cbETH → USDC). */
export default function PortalBorrowLayout({ children }: { children: React.ReactNode }) {
  const appId = getPrivyAppIdServer()
  return <PortalAuthPrivyGate appId={appId}>{children}</PortalAuthPrivyGate>
}
