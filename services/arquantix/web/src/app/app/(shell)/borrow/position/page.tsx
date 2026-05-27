import { Suspense } from 'react'

import { PortalLombardPositionDetailScreen } from '@/components/portal/lombard/PortalLombardPositionDetailScreen'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'

function PortalLombardPositionFallback() {
  return (
    <PortalPageContainer>
      <p className="m-0 font-ui text-[15px] text-v-muted">Loading…</p>
    </PortalPageContainer>
  )
}

export default function PortalLombardPositionPage() {
  return (
    <Suspense fallback={<PortalLombardPositionFallback />}>
      <PortalLombardPositionDetailScreen />
    </Suspense>
  )
}
