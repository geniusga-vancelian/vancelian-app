'use client'

import { cn } from '@/lib/utils'
import { DesignSystemShowcase } from '@/components/design-system/DesignSystemShowcase'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { Container } from '@/components/ui/Container'
import { VEyebrow } from '@/components/design-system/vancelian/VEyebrow'

export default function PortalDesignPage() {
  return (
    <div className="pb-16">
      <PortalPageContainer className="lg:py-12">
        <VEyebrow>Design system</VEyebrow>
        <h1 className="mt-2 mb-0 font-ui text-[28px] font-semibold tracking-v-tight text-v-fg">Design</h1>
        <p className="mt-3 mb-0 max-w-2xl font-ui text-[16px] leading-relaxed text-v-fg-body">
          Modules marketing et composants Vancelian — équivalent de l’onglet Design de l’app mobile.
        </p>
      </PortalPageContainer>
      <div className={cn('border-t border-v-fg-10 bg-v-bg')}>
        <Container className="py-10 lg:py-12">
          <DesignSystemShowcase />
        </Container>
      </div>
    </div>
  )
}
