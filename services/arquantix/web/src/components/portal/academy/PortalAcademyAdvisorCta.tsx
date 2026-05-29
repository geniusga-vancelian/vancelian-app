'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

/** CTA conseiller — handoff `.acd-cta`. */
export function PortalAcademyAdvisorCta() {
  return (
    <section className="acd-cta">
      <div className="acd-cta__body">
        <span className="v-eyebrow">Personal advice</span>
        <h3 className="acd-cta__title">Questions about your situation?</h3>
        <p className="acd-cta__lede">
          Our wealth advisors reply by video or message — by appointment, at no charge.
        </p>
      </div>
      <PortalNavLink href={PORTAL_ROUTES.profile} className="btn btn--primary no-underline">
        <KalaiIcon name="calendar" size={16} />
        Book a meeting
      </PortalNavLink>
    </section>
  )
}
