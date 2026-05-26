'use client'

import { AppDesignSystemShowcase } from '@/components/design-system/app/AppDesignSystemShowcase'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'

/** Design S. — showcase complet du handoff App Vancelian.zip. */
export default function PortalDesignPage() {
  return (
    <div className="pb-8">
      <PortalPageContainer className="max-w-none px-4 py-6 sm:px-6 lg:px-8 lg:py-10">
        <AppDesignSystemShowcase />
      </PortalPageContainer>
    </div>
  )
}
