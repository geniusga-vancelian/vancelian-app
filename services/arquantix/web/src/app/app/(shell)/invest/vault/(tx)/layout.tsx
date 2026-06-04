import { PortalWeb3Boundary } from '@/components/portal/web3/PortalWeb3Boundary'
import { getPortalWeb3LayoutProps } from '@/lib/portal/portalWeb3LayoutProps'

/** Invest vault deposit / withdraw — Wagmi + Privy (aligné wallet/(tx)/swap, R4.5-F4). */
export default async function PortalInvestVaultTxWeb3Layout({
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
