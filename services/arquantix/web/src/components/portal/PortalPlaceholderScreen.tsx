'use client'

import { VEyebrow } from '@/components/design-system/vancelian/VEyebrow'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'

type Props = {
  title: string
  description?: string
}

export function PortalPlaceholderScreen({ title, description }: Props) {
  return (
    <PortalPageContainer>
      <div className="mx-auto max-w-2xl">
        <VEyebrow>Coming soon</VEyebrow>
        <h1 className="mt-2 mb-0 font-ui text-[28px] font-semibold tracking-v-tight text-v-fg">{title}</h1>
        {description ? (
          <p className="mt-3 mb-0 font-ui text-[16px] leading-relaxed text-v-fg-body">{description}</p>
        ) : null}
      </div>
    </PortalPageContainer>
  )
}
