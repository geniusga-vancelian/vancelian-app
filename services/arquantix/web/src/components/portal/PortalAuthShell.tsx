'use client'

import { SectionHero } from '@/components/sections/SectionHero'
import { BrandLogo, type SiteBrandLogo } from '@/components/ui/BrandLogo'
import { PortalBackToWebsiteLink } from '@/components/portal/PortalBackToWebsiteLink'
import { PortalAuthFootnote } from '@/components/portal/PortalAuthFootnote'
import { usePortalAuthContent } from '@/components/portal/PortalAuthContentProvider'
import type { HomeHeroAuthContent } from '@/lib/cms/resolveHomeHeroAuthContent'
import { cn } from '@/lib/utils'

type Props = {
  children: React.ReactNode
  heroContent: HomeHeroAuthContent | null
  brand?: SiteBrandLogo | null
  backToWebsiteLabel?: string
  backToWebsiteHref?: string
  instant?: boolean
  /** Colonne hero vide sur desktop pendant le bootstrap (évite layout single-panel). */
  preserveDesktopHeroColumn?: boolean
}

function PortalAuthHeroPanel({ heroContent }: { heroContent: HomeHeroAuthContent }) {
  return (
    <div className="portal-auth__media">
      <SectionHero
        {...heroContent}
        hideCta
        className="portal-auth__hero"
      />
    </div>
  )
}

export function PortalAuthShell({
  children,
  heroContent,
  brand,
  backToWebsiteLabel = 'Back to the website',
  backToWebsiteHref = '/en',
  instant = false,
  preserveDesktopHeroColumn = false,
}: Props) {
  const authContent = usePortalAuthContent()
  const singlePanel = !heroContent && !preserveDesktopHeroColumn

  return (
    <div className="portal-auth-page">
      <main
        className={cn(
          'portal-auth',
          singlePanel && 'portal-auth--single-panel',
          instant && 'portal-auth--instant',
        )}
      >
        <PortalBackToWebsiteLink
          href={backToWebsiteHref}
          className="portal-auth__back"
          aria-label={backToWebsiteLabel}
        >
          <span className="portal-auth__back-arrow" aria-hidden="true">
            ←
          </span>
          <span>{backToWebsiteLabel}</span>
        </PortalBackToWebsiteLink>

        {heroContent ? (
          <PortalAuthHeroPanel heroContent={heroContent} />
        ) : preserveDesktopHeroColumn ? (
          <div className="portal-auth__media portal-auth__media--placeholder" aria-hidden />
        ) : null}

        <section className="portal-auth__form-wrap" aria-labelledby="portal-auth-form-title">
          <PortalBackToWebsiteLink
            href={backToWebsiteHref}
            className="portal-auth__logo"
            aria-label="Vancelian — home"
          >
            <BrandLogo brand={brand} lockup="horizontal" color="black" className="h-6 w-auto" />
          </PortalBackToWebsiteLink>

          <div className="portal-auth__form-main">{children}</div>

          <PortalAuthFootnote content={authContent.legal} />
        </section>
      </main>
    </div>
  )
}
