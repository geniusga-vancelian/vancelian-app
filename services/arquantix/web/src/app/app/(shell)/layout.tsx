import { getPortalShellBootstrap } from '@/lib/cms/portalShellBootstrap'
import { PortalShell } from '@/components/portal/PortalShell'

export default async function PortalShellLayout({ children }: { children: React.ReactNode }) {
  const { footer: initialFooterData, support: initialSupportContent } = await getPortalShellBootstrap('en')

  return (
    <PortalShell initialFooterData={initialFooterData} initialSupportContent={initialSupportContent}>
      {children}
    </PortalShell>
  )
}
