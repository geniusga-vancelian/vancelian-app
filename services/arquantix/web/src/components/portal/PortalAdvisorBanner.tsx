'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

/** Bannière advisor compacte — handoff `.adv-C` (sidebar portfolio / placer). */
export function PortalAdvisorBanner() {
  return (
    <PortalNavLink href={PORTAL_ROUTES.profile} className="adv-C no-underline">
      <span className="adv-C__ic" aria-hidden>
        <KalaiIcon name="info" size={16} />
      </span>
      <span className="adv-C__body">
        <span className="adv-C__title">Une question ?</span>
        <span className="adv-C__sub">Consultez la FAQ ou contactez votre advisor.</span>
      </span>
      <span className="adv-C__cta">Voir la FAQ</span>
    </PortalNavLink>
  )
}
