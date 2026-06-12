'use client'

import { PortalRouteError } from '@/components/portal/PortalRouteError'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

export default function PortalInvestOfferError(props: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <PortalRouteError
      {...props}
      message="This offer couldn’t be loaded right now."
      backHref={PORTAL_ROUTES.invest}
      backLabel="Back to offers"
    />
  )
}
