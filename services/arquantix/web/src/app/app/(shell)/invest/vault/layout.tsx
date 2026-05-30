import { PortalWeb3Boundary } from '@/components/portal/web3/PortalWeb3Boundary'
import { getPortalWeb3LayoutProps } from '@/lib/portal/portalWeb3LayoutProps'

/** DeFi vault invest — Privy + Wagmi montés une fois (évite le crash iframe lazy modal). */
export default async function PortalInvestVaultWeb3Layout({
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
