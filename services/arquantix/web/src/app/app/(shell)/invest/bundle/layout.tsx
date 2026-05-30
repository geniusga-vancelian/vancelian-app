import { PortalWeb3Boundary } from '@/components/portal/web3/PortalWeb3Boundary'
import { getPortalWeb3LayoutProps } from '@/lib/portal/portalWeb3LayoutProps'

/** Bundle invest / withdraw — Privy + Wagmi for LI.FI signing. */
export default async function PortalBundleInvestWeb3Layout({
  children,
}: {
  children: React.ReactNode
}) {
  const { appId, wagmiCookieHeader } = await getPortalWeb3LayoutProps()

  return (
    <PortalWeb3Boundary appId={appId} wagmiCookieHeader={wagmiCookieHeader}>
      {children}
    </PortalWeb3Boundary>
  )
}
