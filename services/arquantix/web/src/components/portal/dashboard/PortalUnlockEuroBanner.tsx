'use client'

import { AppBanner } from '@/components/design-system/app/AppBanner'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  progressPercent?: number
}

export function PortalUnlockEuroBanner({ progressPercent }: Props) {
  const progress =
    progressPercent != null ? `${Math.max(0, Math.min(100, progressPercent))}% complete` : null

  return (
    <AppBanner
      variant="info"
      title="Unlock Euro account"
      message={
        progress
          ? `Your crypto wallet is ready. Complete registration to add a Euro account (${progress}).`
          : 'Your crypto wallet is ready. Complete registration to add a Euro account and access all investment categories from your crypto balance.'
      }
      ctaLabel="Complete registration"
      ctaHref={PORTAL_ROUTES.registration}
    />
  )
}
