import { PortalAuthShell } from '@/components/portal/PortalAuthShell'
import { PortalAuthContentProvider } from '@/components/portal/PortalAuthContentProvider'
import { getDefaultPortalAuthContent } from '@/lib/cms/portal-auth'

type Props = {
  children: React.ReactNode
}

/** Shell login minimal (defaults CMS) — first paint instant pendant le chargement SSR complet. */
export function PortalAuthBootstrapShell({ children }: Props) {
  const content = getDefaultPortalAuthContent()

  return (
    <PortalAuthContentProvider content={content}>
      <PortalAuthShell
        heroContent={null}
        brand={null}
        backToWebsiteLabel={content.shell.backToWebsiteLabel}
        backToWebsiteHref={content.shell.backToWebsiteHref}
      >
        {children}
      </PortalAuthShell>
    </PortalAuthContentProvider>
  )
}
