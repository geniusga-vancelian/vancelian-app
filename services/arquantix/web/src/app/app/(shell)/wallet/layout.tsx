import { PortalWeb3Boundary } from '@/components/portal/web3/PortalWeb3Boundary'
import { getPortalWeb3LayoutProps } from '@/lib/portal/portalWeb3LayoutProps'

export default async function PortalWalletWeb3Layout({ children }: { children: React.ReactNode }) {
  const { appId, wagmiCookieHeader } = await getPortalWeb3LayoutProps()

  return (
    <PortalWeb3Boundary appId={appId} wagmiCookieHeader={wagmiCookieHeader}>
      {children}
    </PortalWeb3Boundary>
  )
}
