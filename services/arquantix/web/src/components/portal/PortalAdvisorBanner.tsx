'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

/** Compact advisor banner — handoff `.adv-C` (portfolio / placer sidebar). */
export function PortalAdvisorBanner() {
  return (
    <PortalNavLink href={PORTAL_ROUTES.profile} className="adv-C no-underline">
      <span className="adv-C__ic" aria-hidden>
        <KalaiIcon name="info" size={16} />
      </span>
      <span className="adv-C__body">
        <span className="adv-C__title">Questions?</span>
        <span className="adv-C__sub">Browse the FAQ or contact your advisor.</span>
      </span>
      <span className="adv-C__cta">View FAQ</span>
    </PortalNavLink>
  )
}
