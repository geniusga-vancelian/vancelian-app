import { PortalAuthShell } from '@/components/portal/PortalAuthShell'
import { PortalAuthContentProvider } from '@/components/portal/PortalAuthContentProvider'
import { getDefaultPortalAuthContent } from '@/lib/cms/portal-auth'

type Props = {
  children: React.ReactNode
}

/**
 * Shell login minimal — même structure que le shell CMS (hero + formulaire)
 * pour éviter le clignotement pendant le streaming Suspense.
 */
export function PortalAuthBootstrapShell({ children }: Props) {
  const content = getDefaultPortalAuthContent()

  return (
    <PortalAuthContentProvider content={content}>
      <PortalAuthShell
        heroContent={{
          title: content.login.title,
          subtitle: content.login.body,
        }}
        brand={null}
        backToWebsiteLabel={content.shell.backToWebsiteLabel}
        backToWebsiteHref={content.shell.backToWebsiteHref}
      >
        {children}
      </PortalAuthShell>
    </PortalAuthContentProvider>
  )
}
