'use client'

import Link from 'next/link'
import { SectionHero } from '@/components/sections/SectionHero'
import { BrandLogo, type SiteBrandLogo } from '@/components/ui/BrandLogo'
import { PersistentSiteFooter } from '@/components/site/PersistentSiteFooter'
import { PortalAuthFootnote } from '@/components/portal/PortalAuthFootnote'
import { usePortalAuthContent } from '@/components/portal/PortalAuthContentProvider'
import type { HomeHeroAuthContent } from '@/lib/cms/resolveHomeHeroAuthContent'
import type { SiteFooterData } from '@/lib/cms/site-footer'

type Props = {
  children: React.ReactNode
  heroContent: HomeHeroAuthContent | null
  brand?: SiteBrandLogo | null
  initialFooterData?: SiteFooterData
  backToWebsiteLabel?: string
  backToWebsiteHref?: string
}

function PortalAuthHeroPanel({ heroContent }: { heroContent: HomeHeroAuthContent }) {
  return (
    <div className="portal-auth__media">
      <SectionHero
        {...heroContent}
        hideCta
        deferBackgroundVideo
        className="portal-auth__hero"
      />
    </div>
  )
}

export function PortalAuthShell({
  children,
  heroContent,
  brand,
  initialFooterData,
  backToWebsiteLabel = 'Back to the website',
  backToWebsiteHref = '/en',
}: Props) {
  const authContent = usePortalAuthContent()

  return (
    <div className="portal-auth-page">
      <main className="portal-auth">
        <Link href={backToWebsiteHref} className="portal-auth__back" aria-label={backToWebsiteLabel}>
          <span className="portal-auth__back-arrow" aria-hidden="true">
            ←
          </span>
          <span>{backToWebsiteLabel}</span>
        </Link>

        {heroContent ? <PortalAuthHeroPanel heroContent={heroContent} /> : null}

        <section className="portal-auth__form-wrap" aria-labelledby="portal-auth-form-title">
          <Link href={backToWebsiteHref} className="portal-auth__logo" aria-label="Vancelian — home">
            <BrandLogo brand={brand} lockup="horizontal" color="black" className="h-6 w-auto" />
          </Link>

          <div className="portal-auth__form-main">{children}</div>

          <PortalAuthFootnote content={authContent.legal} />
        </section>
      </main>

      <PersistentSiteFooter initialData={initialFooterData} />
    </div>
  )
}
