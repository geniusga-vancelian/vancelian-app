'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

const ADVISOR_PORTRAIT_SRC = '/app-ds/assets/photos/placeholder.jpg'

/** Advisor portrait card — handoff `.adv-A` (portal sidebar). */
export function PortalAdvisorPortraitCard() {
  return (
    <div className="adv-A">
      <div className="adv-A__head">
        <img
          className="adv-A__portrait"
          src={ADVISOR_PORTRAIT_SRC}
          alt="Hélène Marchand, advisor"
          width={56}
          height={56}
        />
        <div className="adv-A__title-block">
          <div className="v-eyebrow adv-A__eyebrow">Your advisor</div>
          <h3 className="adv-A__name">Hélène Marchand</h3>
        </div>
      </div>
      <p className="adv-A__desc">
        Dedicated to your wealth for 3 years. Available Monday to Friday, 9 a.m. – 7 p.m.
      </p>
      <div className="adv-A__actions">
        <PortalNavLink href={PORTAL_ROUTES.profile} className="btn btn--primary btn--sm">
          Book a call
        </PortalNavLink>
        <PortalNavLink href={PORTAL_ROUTES.profile} className="btn btn--secondary btn--sm">
          Message
        </PortalNavLink>
      </div>
    </div>
  )
}
