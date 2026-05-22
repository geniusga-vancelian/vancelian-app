'use client'

/**
 * Adaptateur de présentation entre les données footer (`SiteFooterData`,
 * éditées dans /admin) et le composant DS Footer.
 *
 * Tous les libellés génériques passent par `siteCommonCta` (FR / EN / IT) ;
 * les valeurs CMS restent prioritaires via `getDefaultSiteFooterData(locale)`
 * (cf. `lib/cms/site-footer.ts`). Aucun défaut hardcodé ici : la source
 * unique des fallbacks est `getDefaultSiteFooterData`.
 */

import * as React from 'react'
import { usePathname } from 'next/navigation'

import { cn } from '@/lib/utils'
import { Container } from '@/components/ui/Container'
import DsFooter from '@/components/design-system/Footer'
import type { FooterNavColumn } from '@/components/design-system/Footer'
import { getDefaultSiteFooterData, type SiteFooterData } from '@/lib/cms/site-footer'
import { normalizeVancelianDarkColor } from '@/lib/cms/parseEditorialTitle'
import { getActiveLocaleFromPathname } from '@/lib/i18n/publicLocalizedRouting'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'

function buildNavColumns(
  links: Array<{ label: string; href: string; category?: string }> | undefined,
  defaultCategoryLabel: string,
): FooterNavColumn[] | undefined {
  if (!links?.length) return undefined
  const map = new Map<string, { label: string; href: string }[]>()
  for (const link of links) {
    const title = (link.category?.trim() || defaultCategoryLabel).replace(/\s+/g, ' ')
    if (!map.has(title)) map.set(title, [])
    map.get(title)!.push({ label: link.label, href: link.href })
  }
  return Array.from(map.entries()).map(([title, ls]) => ({ title, links: ls }))
}

export interface FooterProps extends React.HTMLAttributes<HTMLElement> {
  /** Données complètes du footer global (prioritaire sur les props legacy). */
  data?: SiteFooterData
  copyright?: string
  description?: string
  links?: Array<{
    label: string
    href: string
    category?: string
  }>
}

export function Footer({ data, copyright, description, links, className, ...props }: FooterProps) {
  const pathname = usePathname() ?? ''
  const loc = getActiveLocaleFromPathname(pathname)
  const defaults = getDefaultSiteFooterData(loc)

  const resolved: SiteFooterData = data
    ? data
    : {
        ...defaults,
        copyright: copyright ?? defaults.copyright,
        description: description ?? defaults.description,
        links: links ?? defaults.links,
      }

  const defaultCategoryLabel = siteCommonCta(loc, 'footer_links_default_category')
  const navColumns = buildNavColumns(resolved.links, defaultCategoryLabel)
  // Vancelian DS — fond dark officiel `#141208` (anthracite chaud, jamais noir pur).
  const bg = normalizeVancelianDarkColor(resolved.backgroundColor || 'var(--v-dark-bg)')

  return (
    <div
      data-testid="site-footer"
      data-nav-surface="dark"
      role="contentinfo"
      className={cn('w-full border-t border-white/[0.08]', className)}
      style={{ backgroundColor: bg }}
      {...props}
    >
      <Container className="pt-20 pb-8">
        <div className="[&>footer]:w-full [&>footer]:!bg-transparent">
          <DsFooter
            copyrightText={resolved.copyright || defaults.copyright}
            tagline={resolved.description || defaults.description}
            companyAddress={resolved.companyAddress || defaults.companyAddress}
            secondaryNote={resolved.secondaryNote || defaults.secondaryNote}
            navColumns={navColumns}
            legalTexts={resolved.legalTexts}
            logoUrl={resolved.logoUrl}
            logoAlt={resolved.logoAlt}
            logoMediaInvert={resolved.logoMediaInvert}
            newsletterVisible={resolved.newsletterVisible}
            newsletterTitle={resolved.newsletterTitle}
            newsletterPlaceholder={resolved.newsletterPlaceholder}
            newsletterButtonLabel={resolved.newsletterButtonLabel}
            newsletterSubmittingLabel={siteCommonCta(loc, 'footer_newsletter_submitting')}
            newsletterSuccessMessage={siteCommonCta(loc, 'footer_newsletter_success')}
            newsletterAlreadySubscribedMessage={siteCommonCta(
              loc,
              'footer_newsletter_already_subscribed',
            )}
            newsletterInvalidEmailMessage={siteCommonCta(loc, 'footer_newsletter_invalid_email')}
            newsletterErrorMessage={siteCommonCta(loc, 'footer_newsletter_error')}
            socialLinks={resolved.socialLinks}
          />
        </div>
      </Container>
    </div>
  )
}
