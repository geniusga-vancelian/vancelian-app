import { PortalWeb3Boundary } from '@/components/portal/web3/PortalWeb3Boundary'
import { getPortalWeb3LayoutProps } from '@/lib/portal/portalWeb3LayoutProps'

/** Invest bundle — Wagmi + Privy pour confirmation / exécution on-chain (aligné vault/(tx), R4.5-F5-A). */
export default async function PortalInvestBundleTxWeb3Layout({
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
