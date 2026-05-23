import { PortalAuthShell } from '@/components/portal/PortalAuthShell'
import { PortalAuthContentProvider } from '@/components/portal/PortalAuthContentProvider'
import { resolveHomeHeroAuthContent } from '@/lib/cms/resolveHomeHeroAuthContent'
import { getPortalAuthContent } from '@/lib/cms/portal-auth'
import { getSiteBrandLogo } from '@/lib/cms/site-footer'
import { defaultLocale } from '@/config/locales'

type Props = {
  children: React.ReactNode
}

/** Shell login complet — hero CMS + copy admin (streamé après le bootstrap). */
export async function PortalLoginCmsShell({ children }: Props) {
  const [heroContent, brand, portalAuthContent] = await Promise.all([
    resolveHomeHeroAuthContent(),
    getSiteBrandLogo(defaultLocale),
    getPortalAuthContent(),
  ])

  return (
    <PortalAuthContentProvider content={portalAuthContent}>
      <PortalAuthShell
        heroContent={heroContent}
        brand={brand}
        backToWebsiteLabel={portalAuthContent.shell.backToWebsiteLabel}
        backToWebsiteHref={portalAuthContent.shell.backToWebsiteHref}
      >
        {children}
      </PortalAuthShell>
    </PortalAuthContentProvider>
  )
}
