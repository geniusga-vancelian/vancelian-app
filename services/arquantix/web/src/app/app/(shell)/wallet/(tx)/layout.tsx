import { PortalWeb3Boundary } from '@/components/portal/web3/PortalWeb3Boundary'
import { getPortalWeb3LayoutProps } from '@/lib/portal/portalWeb3LayoutProps'

/** Wallet transaction routes only — swap, create, deposit, withdraw (R4.5-F2). */
export default async function PortalWalletTxWeb3Layout({ children }: { children: React.ReactNode }) {
  const { appId, wagmiCookieHeader } = await getPortalWeb3LayoutProps()

  return (
    <PortalWeb3Boundary appId={appId} wagmiCookieHeader={wagmiCookieHeader}>
      {children}
    </PortalWeb3Boundary>
  )
}
