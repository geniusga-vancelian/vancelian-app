'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { Button } from '@/components/ui/button'
import { isPortalEuroFeaturesEnabled } from '@/lib/portal/portalEuroVisibility'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

/** Placeholder local — parcours registration web à brancher sur l’API mobile. */
export default function PortalRegistrationPage() {
  const euroEnabled = isPortalEuroFeaturesEnabled()

  return (
    <PortalPageContainer>
      <div className="mx-auto flex max-w-lg flex-col gap-4 py-8">
        <h1 className="m-0 font-ui text-[24px] font-semibold text-v-fg">Complete registration</h1>
        <p className="m-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
          {euroEnabled
            ? 'Finish your account verification to unlock your Euro account. Your crypto wallet remains available throughout this process.'
            : 'Finish your account verification to access all investment categories. Your crypto wallet remains available throughout this process.'}
        </p>
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">
          Registration screens will be connected here. For now, return to your dashboard to keep
          using your crypto wallet.
        </p>
        <Button type="button" asChild className="w-fit">
          <PortalNavLink href={PORTAL_ROUTES.dashboard}>Back to dashboard</PortalNavLink>
        </Button>
      </div>
    </PortalPageContainer>
  )
}
