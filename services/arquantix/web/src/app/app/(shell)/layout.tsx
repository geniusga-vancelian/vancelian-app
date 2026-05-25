import { getSiteFooterData } from '@/lib/cms/site-footer'
import { getPortalSupportContent } from '@/lib/cms/portal-support'
import { PortalShell } from '@/components/portal/PortalShell'
import { PortalWeb3Providers } from '@/components/portal/PortalWeb3Providers'

export default async function PortalShellLayout({ children }: { children: React.ReactNode }) {
  let initialFooterData: Awaited<ReturnType<typeof getSiteFooterData>> | undefined
  let initialSupportContent: Awaited<ReturnType<typeof getPortalSupportContent>> | undefined
  try {
    initialFooterData = await getSiteFooterData('fr')
  } catch {
    initialFooterData = undefined
  }
  try {
    initialSupportContent = await getPortalSupportContent('fr')
  } catch {
    initialSupportContent = undefined
  }

  return (
    <PortalWeb3Providers>
      <PortalShell initialFooterData={initialFooterData} initialSupportContent={initialSupportContent}>
        {children}
      </PortalShell>
    </PortalWeb3Providers>
  )
}
