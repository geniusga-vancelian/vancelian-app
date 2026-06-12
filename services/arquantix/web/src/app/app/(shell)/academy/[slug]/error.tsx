'use client'

import { PortalRouteError } from '@/components/portal/PortalRouteError'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

export default function PortalAcademyArticleError(props: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <PortalRouteError
      {...props}
      message="This article couldn’t be loaded right now."
      backHref={PORTAL_ROUTES.academy}
      backLabel="Back to Academy"
    />
  )
}
