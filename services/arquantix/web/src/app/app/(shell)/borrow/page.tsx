import { Suspense } from 'react'

import { PortalLombardFlow } from '@/components/portal/lombard/PortalLombardFlow'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'

function PortalBorrowFallback() {
  return (
    <PortalPageContainer>
      <p className="m-0 font-ui text-[15px] text-v-muted">Loading…</p>
    </PortalPageContainer>
  )
}

export default function PortalBorrowPage() {
  return (
    <Suspense fallback={<PortalBorrowFallback />}>
      <PortalLombardFlow />
    </Suspense>
  )
}
