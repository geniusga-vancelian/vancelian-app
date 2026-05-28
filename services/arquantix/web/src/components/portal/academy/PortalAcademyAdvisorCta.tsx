'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

/** CTA conseiller — handoff `.acd-cta`. */
export function PortalAcademyAdvisorCta() {
  return (
    <section className="acd-cta">
      <div className="acd-cta__body">
        <span className="v-eyebrow">Conseil personnalisé</span>
        <h3 className="acd-cta__title">Une question sur votre situation ?</h3>
        <p className="acd-cta__lede">
          Nos conseillers patrimoniaux répondent en visio ou par message — sur rendez-vous, sans frais.
        </p>
      </div>
      <PortalNavLink href={PORTAL_ROUTES.profile} className="btn btn--primary no-underline">
        <KalaiIcon name="calendar" size={14} />
        Prendre rendez-vous
      </PortalNavLink>
    </section>
  )
}
