'use client'

import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalAcademyFeaturedList } from '@/components/portal/academy/PortalAcademyFeaturedList'
import type { PortalAcademyArticle } from '@/lib/portal/academyHubTypes'

type Props = {
  highlighted: PortalAcademyArticle[]
}

/** Sidebar Académie — highlighted + advisor (handoff `col-side`). */
export function PortalAcademySidebar({ highlighted }: Props) {
  return (
    <>
      <PortalAcademyFeaturedList items={highlighted} />
      <PortalAdvisorBanner />
    </>
  )
}
