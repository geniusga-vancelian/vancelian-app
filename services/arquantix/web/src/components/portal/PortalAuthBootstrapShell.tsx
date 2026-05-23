import { PortalAuthShell } from '@/components/portal/PortalAuthShell'
import { PortalAuthContentProvider } from '@/components/portal/PortalAuthContentProvider'
import { getDefaultPortalAuthContent } from '@/lib/cms/portal-auth'

type Props = {
  children: React.ReactNode
  /** Après sign-out : pas de fade-in 300ms sur le shell login. */
  instant?: boolean
  /** Grille 2 colonnes desktop pendant le chargement CMS. */
  preserveDesktopHeroColumn?: boolean
}

/**
 * Shell login minimal — même structure que le shell CMS (hero + formulaire)
 * pour éviter le clignotement pendant le streaming Suspense.
 */
export function PortalAuthBootstrapShell({
  children,
  instant = false,
  preserveDesktopHeroColumn = true,
}: Props) {
  const content = getDefaultPortalAuthContent()

  return (
    <PortalAuthContentProvider content={content}>
      <PortalAuthShell
        heroContent={null}
        brand={null}
        instant={instant}
        preserveDesktopHeroColumn={preserveDesktopHeroColumn}
        backToWebsiteLabel={content.shell.backToWebsiteLabel}
        backToWebsiteHref={content.shell.backToWebsiteHref}
      >
        {children}
      </PortalAuthShell>
    </PortalAuthContentProvider>
  )
}
