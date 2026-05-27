import { cookies } from 'next/headers'

import { getPortalShellBootstrap } from '@/lib/cms/portalShellBootstrap'
import { PortalShell } from '@/components/portal/PortalShell'
import { PortalWeb3Providers } from '@/components/portal/PortalWeb3Providers'
import { buildWagmiCookieHeader } from '@/lib/wallet/wagmiCookieHeader'

export default async function PortalShellLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies()
  const wagmiCookieHeader = buildWagmiCookieHeader(cookieStore.get('wagmi.store')?.value)

  const { footer: initialFooterData, support: initialSupportContent } = await getPortalShellBootstrap('en')

  return (
    <PortalWeb3Providers wagmiCookieHeader={wagmiCookieHeader}>
      <PortalShell initialFooterData={initialFooterData} initialSupportContent={initialSupportContent}>
        {children}
      </PortalShell>
    </PortalWeb3Providers>
  )
}
